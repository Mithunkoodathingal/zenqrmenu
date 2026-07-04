"""
==============================================================
payments/services.py
==============================================================

Business Logic Layer for the Payments App

This module contains reusable business logic for payment
processing, order calculations, gateway calculations,
receipt generation, invoice numbering, settlements,
and payment validation.

Views should remain thin.

APIView
    │
    ▼
services.py
    │
    ▼
Models / Database

The functions in this module should:

✔ Never depend on HTTP requests
✔ Never return DRF Response objects
✔ Never contain APIView logic
✔ Be reusable across APIs, Celery tasks,
  management commands, webhooks and signals
✔ Raise exceptions instead of returning
  HTTP error responses

--------------------------------------------------------------
Module Layout
--------------------------------------------------------------

Part 1
-------
Shared Helpers

    money()
    round_money()
    percentage()
    validate_amount()
    get_gateway_settings()
    get_receipt()
    refunded_amount()

Part 2
-------
Order Calculations

    calculate_subtotal()
    calculate_discount()
    calculate_tax()
    calculate_delivery_charge()
    calculate_packing_charge()
    calculate_grand_total()
    update_order_totals()

Part 3
-------
Gateway Calculations

    calculate_gateway_fee()
    calculate_gateway_tax()
    calculate_net_amount()
    calculate_settlement_amount()
    calculate_platform_commission()

Part 4
-------
Transaction / Invoice / Receipt

    generate_invoice_number()
    generate_receipt_number()
    create_receipt()
    ensure_receipt()
    mark_receipt_downloaded()
    mark_receipt_printed()
    mark_receipt_emailed()
    mark_receipt_whatsapp_sent()

Part 5
-------
Utilities

    normalize_phone()
    format_currency()
    validate_payment()

Future Parts
------------

Part 6
    Refund Helpers

Part 7
    Reconciliation Helpers

Part 8
    Dashboard Helpers

Part 9
    Reporting Helpers

==============================================================
Design Rules
==============================================================

1. All money calculations must use Decimal.

2. Never duplicate calculations in API views.

3. Never access request.user here.

4. Never import DRF serializers.

5. Never import APIView classes.

6. Every monetary calculation should pass through
   the money() helper.

7. All updates to Order totals should go through
   update_order_totals().

8. Receipt creation must always use
   create_receipt().

9. Invoice numbers must always be generated using
   generate_invoice_number().

10. Payment gateway calculations must use the
    restaurant's configured gateway settings.

==============================================================
"""

# ==========================================================
# Imports
# ==========================================================

from decimal import Decimal, ROUND_HALF_UP
import random
import string
import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import csv
from io import BytesIO, StringIO

from requests import Response
from rest_framework import request
# =============================================================================
# Third-Party Imports
# =============================================================================

import razorpay
from openpyxl import Workbook

from django.db import models
from payments.models import PaymentRefund
from django.db.models import Sum, Count, Q
import re

import restaurant
# from .views.payment_settings import get_payment_settings
from .models import (
    PaymentAuditLog,
    PaymentTransaction,
    PaymentRefund,
    Receipt,
    RestaurantGatewaySettings,
)
from restaurant.models import (
    Order,
    OrderItem,
    Restaurant,
)

# ==========================================================
# Constants
# ==========================================================

TWOPLACES = Decimal("0.01")

DEFAULT_GATEWAY_PERCENT = Decimal("2.00")

DEFAULT_GATEWAY_GST = Decimal("5.00")

DEFAULT_TAX_PERCENT = Decimal("0.00")

# ==========================================================
# Shared Helpers
# ==========================================================

# ==========================================================
# Decimal Helpers
# ==========================================================

def money(value):

    """
    Safely convert any value into Decimal
    rounded to 2 decimal places.
    """

    if value is None:

        return Decimal("0.00")

    return Decimal(str(value)).quantize(

        TWOPLACES,

        rounding=ROUND_HALF_UP,

    )


def round_money(value):

    return money(value)

#=========================================================
        #------IMPORTED FROM VIEWS-------
#=========================================================

def get_restaurant(request):

    try:
        return Restaurant.objects.get(owner=request.user)

    except Restaurant.DoesNotExist:
        return None


def create_audit_log(
    restaurant,
    action,
    description,
    payment=None,
    request=None,
):

    PaymentAuditLog.objects.create(

        restaurant=restaurant,

        payment=payment,

        action=action,

        description=description,

        ip_address=(
            request.META.get("REMOTE_ADDR")
            if request else None
        ),
    )

def get_restaurant_client(restaurant):

    settings_obj = get_payment_settings(
        restaurant
    )

    if not settings_obj.is_active:

        raise ValidationError(
            "Payments are disabled."
        )

    if not settings_obj.accept_online:

        raise ValidationError(
            "Online payment is disabled."
        )

    if not settings_obj.razorpay_key_id:

        raise ValidationError(
            "Missing Razorpay Key ID."
        )

    if not settings_obj.razorpay_key_secret:

        raise ValidationError(
            "Missing Razorpay Key Secret."
        )

    return razorpay.Client(
        auth=(
            settings_obj.razorpay_key_id,
            settings_obj.razorpay_key_secret,
        )
    )

def verify_razorpay_credentials(settings_obj):

    try:

        client = razorpay.Client(

            auth=(
                settings_obj.razorpay_key_id,
                settings_obj.razorpay_key_secret,
            )
        )

        client.order.all(
            {"count": 1}
        )

        settings_obj.verified = True

        settings_obj.verified_at = timezone.now()

        settings_obj.last_verified_at = timezone.now()

        settings_obj.save(
            update_fields=[
                "verified",
                "verified_at",
                "last_verified_at",
            ]
        )

        return True, None

    except Exception as e:

        settings_obj.verified = False

        settings_obj.save(
            update_fields=["verified"]
        )

        return False, str(e)
    


# ==========================================================
# Total Helpers
# ==========================================================

def sum_order_items(order):

    """
    Returns subtotal of all order items
    including add-ons.

    Does NOT include:

    - tax
    - packing
    - delivery
    - discounts
    """

    total = Decimal("0.00")

    items = (

        order.order_items

        .select_related("food_item")

        .prefetch_related("selected_addons")

    )

    for item in items:

        food_price = money(
            item.food_item.price
        )

        addon_total = Decimal("0.00")

        for addon in item.selected_addons.all():

            addon_total += money(
                addon.price
            )

        line_total = (

            food_price +

            addon_total

        ) * item.quantity

        total += line_total

    return round_money(total)

# ==========================================================
# Percentage Helper
# ==========================================================

def percentage(amount, percent):

    amount = money(amount)

    percent = money(percent)

    return round_money(

        amount *

        percent /

        Decimal("100")

    )

# ==========================================================
# Amount Validation
# ==========================================================

def validate_amount(amount):

    amount = money(amount)

    if amount <= Decimal("0.00"):

        raise ValidationError(

            "Amount must be greater than zero."

        )

    return amount

# ==========================================================
# Payment Settings Helper
# ==========================================================

def get_payment_settings(restaurant):
    """
    Returns the payment gateway settings for a restaurant.
    Creates them if they do not already exist.
    """

    settings_obj, _ = RestaurantGatewaySettings.objects.get_or_create(
        restaurant=restaurant
    )

    return settings_obj

# ==========================================================
# Restaurant Payment Settings
# ==========================================================

def get_gateway_percentage(

    restaurant,

):

    """
    Currently returns default gateway fee.

    Later this can be replaced by
    restaurant specific settings.
    """

    return DEFAULT_GATEWAY_PERCENT


def get_gateway_tax_percentage(

    restaurant,

):

    return DEFAULT_GATEWAY_GST


def get_tax_percentage(restaurant):

    if not restaurant.tax_enabled:
        return Decimal("0.00")

    return money(
        restaurant.tax_percentage
    )

# ==========================================================
# Receipt Helper
# ==========================================================

def get_receipt(payment):

    receipt, created = Receipt.objects.get_or_create(

        payment=payment

    )

    return receipt

# ==========================================================
# Refund Helper
# ==========================================================

def refunded_amount(payment):

    total = Decimal("0.00")

    refunds = PaymentRefund.objects.filter(

        payment=payment,

        status="processed",

    )

    for refund in refunds:

        total += money(

            refund.amount

        )

    return round_money(total)

# ==========================================================
# Transaction Wrapper
# ==========================================================

def atomic():

    """
    Convenience decorator.

    Usage:

    @atomic()
    def my_function():
        ...
    """

    return transaction.atomic

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        #  ORDER CALCULATIONS
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# ==========================================================
# ORDER CALCULATIONS
# Part 2A
# ==========================================================

# ----------------------------------------------------------
# Calculate Subtotal
# ----------------------------------------------------------

def calculate_subtotal(order):
    """
    Calculates the subtotal of all order items,
    including selected add-ons.

    Returns
    -------
    Decimal
    """

    subtotal = Decimal("0.00")

    items = (
        order.order_items
        .select_related("food_item")
        .prefetch_related("selected_addons")
    )

    for item in items:

        food_price = money(
            item.food_item.price
        )

        addon_price = Decimal("0.00")

        for addon in item.selected_addons.all():

            addon_price += money(
                addon.price
            )

        line_total = (

            food_price +

            addon_price

        ) * item.quantity

        subtotal += line_total

    return round_money(subtotal)


# ----------------------------------------------------------
# Calculate Discount
# ----------------------------------------------------------

def calculate_discount(
    order,
    subtotal,
):
    """
    Calculates discount.

    Currently returns the stored value.

    Future:
        - Coupon Codes
        - Promo Codes
        - Membership Discount
        - Happy Hours
        - Festival Offers
    """

    subtotal = money(subtotal)

    discount = money(
        order.discount_amount
    )

    # Never allow discount
    # greater than subtotal

    if discount > subtotal:

        discount = subtotal

    return round_money(
        discount
    )


# ----------------------------------------------------------
# Calculate Tax
# ----------------------------------------------------------

def calculate_tax(
    order,
    subtotal,
    discount,
):
    """
    Calculates restaurant tax.

    Supports:

    • GST
    • VAT
    • Sales Tax

    Automatically splits GST into

    CGST + SGST

    OR

    IGST
    """

    restaurant = order.restaurant

    subtotal = money(subtotal)

    discount = money(discount)

    taxable_amount = subtotal - discount

    if taxable_amount < Decimal("0.00"):

        taxable_amount = Decimal("0.00")

    # ------------------------------------------
    # Tax Disabled
    # ------------------------------------------

    if not restaurant.tax_enabled:

        return {

            "tax": Decimal("0.00"),

            "cgst": Decimal("0.00"),

            "sgst": Decimal("0.00"),

            "igst": Decimal("0.00"),

        }

    # ------------------------------------------
    # Calculate Tax
    # ------------------------------------------

    tax = percentage(

        taxable_amount,

        restaurant.tax_percentage,

    )

    cgst = Decimal("0.00")

    sgst = Decimal("0.00")

    igst = Decimal("0.00")

    # ------------------------------------------
    # GST
    # ------------------------------------------

    if restaurant.tax_name.lower() == "gst":

        if (

            restaurant.country.lower()

            ==

            order.customer_country.lower()

        ) and (

            restaurant.state.lower()

            ==

            order.customer_state.lower()

        ):

            cgst = round_money(

                tax / Decimal("2")

            )

            sgst = round_money(

                tax / Decimal("2")

            )

        else:

            igst = round_money(

                tax

            )

    # ------------------------------------------
    # VAT / Sales Tax
    # ------------------------------------------

    else:

        tax = round_money(
            tax
        )

    # ------------------------------------------
    # Inclusive Tax
    # ------------------------------------------

    if restaurant.prices_include_tax:

        included_tax = round_money(

            taxable_amount *

            restaurant.tax_percentage /

            (

                Decimal("100.00")

                +

                restaurant.tax_percentage

            )

        )

        tax = included_tax

        if restaurant.tax_name.lower() == "gst":

            if igst > Decimal("0.00"):

                igst = included_tax

                cgst = Decimal("0.00")

                sgst = Decimal("0.00")

            else:

                cgst = round_money(

                    included_tax /

                    Decimal("2")

                )

                sgst = round_money(

                    included_tax /

                    Decimal("2")

                )

    return {

        "tax": round_money(tax),

        "cgst": round_money(cgst),

        "sgst": round_money(sgst),

        "igst": round_money(igst),

    }

# ==========================================================
# ORDER CALCULATIONS
# Part 2B
# ==========================================================

# ----------------------------------------------------------
# Calculate Delivery Charge
# ----------------------------------------------------------

def calculate_delivery_charge(
    order,
    subtotal,
):
    """
    Calculate delivery charge.

    Rules

    • Only for delivery orders

    • Free if subtotal reaches
      restaurant minimum free delivery amount.

    • Otherwise:

        distance × charge_per_km
    """

    restaurant = order.restaurant

    if order.order_type != "delivery":

        return Decimal("0.00")

    subtotal = money(subtotal)

    distance = money(
        order.delivery_distance_km
    )

    # No distance

    if distance <= Decimal("0.00"):

        return Decimal("0.00")

    # Free delivery

    if (

        subtotal >=

        money(
            restaurant.minimum_delivery_order
        )

        and

        distance <=

        money(
            restaurant.free_delivery_radius_km
        )

    ):

        return Decimal("0.00")

    charge = (

        distance *

        money(
            restaurant.delivery_charge_per_km
        )

    )

    return round_money(charge)


# ----------------------------------------------------------
# Calculate Packing Charge
# ----------------------------------------------------------

def calculate_packing_charge(
    order,
):
    """
    Reserved for future.

    Restaurants may define

    packing charge

    per order

    or

    per item.

    Currently returns the stored value.
    """

    return round_money(

        order.packing_charge

    )


# ----------------------------------------------------------
# Calculate Grand Total
# ----------------------------------------------------------

def calculate_grand_total(

    subtotal,

    discount,

    tax,

    delivery,

    packing,

    tip,

    round_off,

):
    """
    Pure calculation.

    No ORM.

    No database.

    Only arithmetic.
    """

    total = (

        money(subtotal)

        -

        money(discount)

        +

        money(tax)

        +

        money(delivery)

        +

        money(packing)

        +

        money(tip)

        +

        money(round_off)

    )

    if total < Decimal("0.00"):

        total = Decimal("0.00")

    return round_money(total)


# ----------------------------------------------------------
# Update Order Totals
# ----------------------------------------------------------

@transaction.atomic
def update_order_totals(
    order,
):
    """
    Calculates every monetary value once.

    Updates

    subtotal

    discount

    tax

    delivery

    packing

    grand total

    cached total

    Returns

    Updated order.
    """

    # ----------------------------------------
    # Calculate Once
    # ----------------------------------------

    subtotal = calculate_subtotal(
        order
    )

    discount = calculate_discount(

        order,

        subtotal,

    )

    taxes = calculate_tax(

        order,

        subtotal,

        discount,

    )

    delivery = calculate_delivery_charge(

        order,

        subtotal,

    )

    packing = calculate_packing_charge(
        order
    )

    tip = money(
        order.tip_amount
    )

    round_off = money(
        order.round_off
    )

    grand_total = calculate_grand_total(

        subtotal=subtotal,

        discount=discount,

        tax=taxes["tax"],

        delivery=delivery,

        packing=packing,

        tip=tip,

        round_off=round_off,

    )

    # ----------------------------------------
    # Update Model
    # ----------------------------------------

    order.subtotal = subtotal

    order.discount_amount = discount

    order.tax_amount = taxes["tax"]

    order.cgst = taxes["cgst"]

    order.sgst = taxes["sgst"]

    order.igst = taxes["igst"]

    order.delivery_charge = delivery

    order.packing_charge = packing

    order.tip_amount = tip

    order.round_off = round_off

    order.grand_total = grand_total

    order.total_price_cached = grand_total

    order.save(

        update_fields=[

            "subtotal",

            "discount_amount",

            "tax_amount",

            "cgst",

            "sgst",

            "igst",

            "delivery_charge",

            "packing_charge",

            "tip_amount",

            "round_off",

            "grand_total",

            "total_price_cached",

        ]

    )

    return order

# ==========================================================
# GATEWAY CALCULATIONS
# Part 3
# ==========================================================

# ==========================================================
# Gateway Settings
# ==========================================================

def get_gateway_settings(restaurant):
    """
    Returns the payment gateway settings for a restaurant.
    Creates a default record if one does not exist.
    """

    settings_obj, _ = RestaurantGatewaySettings.objects.get_or_create(
        restaurant=restaurant
    )

    return settings_obj

# ==========================================================
# Gateway Fee
# ==========================================================

def calculate_gateway_fee(
    restaurant,
    amount,
):
    """
    Calculates payment gateway fee using the
    restaurant's configured gateway percentage.
    """

    amount = money(amount)

    if amount <= Decimal("0.00"):
        return Decimal("0.00")

    settings_obj = get_gateway_settings(
        restaurant
    )

    fee_percentage = money(
        settings_obj.gateway_fee_percentage
    )

    fee = percentage(
        amount,
        fee_percentage,
    )

    return round_money(fee)


# ==========================================================
# Gateway Tax
# ==========================================================

def calculate_gateway_tax(
    restaurant,
    gateway_fee,
):
    """
    Calculates GST/VAT on the gateway fee using
    the restaurant's configured value.
    """

    gateway_fee = money(gateway_fee)

    if gateway_fee <= Decimal("0.00"):
        return Decimal("0.00")

    settings_obj = get_gateway_settings(
        restaurant
    )

    tax_percentage = money(
        settings_obj.gateway_tax_percentage
    )

    gateway_tax = percentage(
        gateway_fee,
        tax_percentage,
    )

    return round_money(gateway_tax)

# ==========================================================
# Net Settlement Amount
# ==========================================================

def calculate_net_amount(
    amount,
    gateway_fee,
    gateway_tax,
):
    """
    Restaurant settlement amount after gateway charges.
    """

    amount = money(amount)

    gateway_fee = money(gateway_fee)

    gateway_tax = money(gateway_tax)

    net_amount = (
        amount
        - gateway_fee
        - gateway_tax
    )

    if net_amount < Decimal("0.00"):
        net_amount = Decimal("0.00")

    return round_money(net_amount)


# ==========================================================
# Settlement Amount
# ==========================================================

def calculate_settlement_amount(
    payment,
):
    """
    Calculates the amount that will settle
    to the restaurant account.
    """

    return calculate_net_amount(
        amount=payment.amount,
        gateway_fee=payment.gateway_fee,
        gateway_tax=payment.gateway_tax,
    )

# ==========================================================
# Platform Commission
# ==========================================================

def calculate_platform_commission(
    restaurant,
    amount,
):
    """
    Reserved for future SaaS commissions.

    Currently returns zero.
    """

    return Decimal("0.00")


# ==========================================================
# TRANSACTION / INVOICE / RECEIPT GENERATORS
# Part 4A
# ==========================================================

# ----------------------------------------------------------
# Generate Invoice Number
# ----------------------------------------------------------

# ==========================================================
# Generate Invoice Number
# ==========================================================

def generate_invoice_number(
    restaurant,
):
    """
    Generate a unique invoice number for a restaurant.

    Format

        INV-20260704-000001

    Example

        INV-20260704-000001
        INV-20260704-000002
        INV-20260704-000003

    Invoice numbering is maintained
    independently for each restaurant.
    """

    prefix = (
        restaurant.invoice_prefix or "INV"
    ).upper()

    date_part = timezone.localdate().strftime(
        "%Y%m%d"
    )

    base = f"{prefix}-{date_part}"

    # ------------------------------------------
    # Find last invoice for THIS restaurant
    # ------------------------------------------

    last_receipt = (

        Receipt.objects

        .filter(

            payment__restaurant=restaurant,

            invoice_number__startswith=base,

        )

        .order_by("-invoice_number")

        .first()

    )

    # ------------------------------------------
    # Determine next sequence
    # ------------------------------------------

    sequence = 1

    if last_receipt:

        try:

            sequence = (

                int(

                    last_receipt.invoice_number

                    .rsplit("-", 1)[1]

                )

                + 1

            )

        except (

            ValueError,

            IndexError,

        ):

            sequence = 1

    # ------------------------------------------
    # Build invoice number
    # ------------------------------------------

    while True:

        invoice_number = (

            f"{base}-{sequence:06d}"

        )

        exists = Receipt.objects.filter(

            payment__restaurant=restaurant,

            invoice_number=invoice_number,

        ).exists()

        if not exists:

            return invoice_number

        sequence += 1


# ----------------------------------------------------------
# Generate Receipt Number
# ----------------------------------------------------------

def generate_receipt_number(
    restaurant,
):
    """
    Currently uses the invoice number.

    Separated for future expansion.

    Example

    Receipt:
        RCPT-20260704-000001

    Invoice:
        INV-20260704-000001
    """

    return generate_invoice_number(
        restaurant
    )


# ----------------------------------------------------------
# Create Receipt
# ----------------------------------------------------------

@transaction.atomic
def create_receipt(
    payment,
    notes="",
):

    if Receipt.objects.filter(
        payment=payment
    ).exists():

        raise ValidationError(
            "Receipt already exists."
        )

    receipt = Receipt.objects.create(

        restaurant=payment.restaurant,

        payment=payment,

        invoice_number=generate_invoice_number(
            payment.restaurant
        ),

        invoice_date=timezone.now(),

        notes=notes,

    )

    return receipt


# ----------------------------------------------------------
# Ensure Receipt
# ----------------------------------------------------------

@transaction.atomic
def ensure_receipt(
    payment,
):
    """
    Returns the existing receipt.

    Creates one if necessary.

    Safe to call multiple times.
    """

    receipt, created = (

        Receipt.objects

        .get_or_create(

            payment=payment,

            defaults={

                "invoice_number":

                    generate_invoice_number(
                        payment.restaurant
                    ),

                "invoice_date":

                    timezone.now(),

            }

        )

    )

    return receipt


# ==========================================================
# RECEIPT STATUS UPDATES
# Part 4B
# ==========================================================

# ----------------------------------------------------------
# Mark Receipt Downloaded
# ----------------------------------------------------------

@transaction.atomic
def mark_receipt_downloaded(
    receipt,
):
    """
    Updates receipt download statistics.
    """

    receipt.download_count += 1

    receipt.last_downloaded_at = timezone.now()

    receipt.save(
        update_fields=[
            "download_count",
            "last_downloaded_at",
        ]
    )

    return receipt


# ----------------------------------------------------------
# Mark Receipt Printed
# ----------------------------------------------------------

@transaction.atomic
def mark_receipt_printed(
    receipt,
):
    """
    Marks a receipt as printed.
    """

    receipt.printed = True

    receipt.printed_at = timezone.now()

    receipt.save(
        update_fields=[
            "printed",
            "printed_at",
        ]
    )

    return receipt


# ----------------------------------------------------------
# Mark Receipt Emailed
# ----------------------------------------------------------

@transaction.atomic
def mark_receipt_emailed(
    receipt,
    email_address=None,
):
    """
    Marks receipt as emailed.
    """

    receipt.email_sent = True

    receipt.email_sent_at = timezone.now()

    if email_address:

        receipt.emailed_to = email_address

    update_fields = [

        "email_sent",

        "email_sent_at",

    ]

    if email_address:

        update_fields.append(
            "emailed_to"
        )

    receipt.save(
        update_fields=update_fields
    )

    return receipt


# ----------------------------------------------------------
# Mark Receipt WhatsApp Sent
# ----------------------------------------------------------

@transaction.atomic
def mark_receipt_whatsapp_sent(
    receipt,
    whatsapp_number=None,
):
    """
    Marks receipt as sent via WhatsApp.
    """

    receipt.whatsapp_sent = True

    receipt.whatsapp_sent_at = timezone.now()

    if whatsapp_number:

        receipt.whatsapp_number = whatsapp_number

    update_fields = [

        "whatsapp_sent",

        "whatsapp_sent_at",

    ]

    if whatsapp_number:

        update_fields.append(
            "whatsapp_number"
        )

    receipt.save(
        update_fields=update_fields
    )

    return receipt


# ==========================================================
# UTILITIES
# Part 5
# ==========================================================

# ----------------------------------------------------------
# Normalize Phone Number
# ----------------------------------------------------------

def normalize_phone(
    phone_number,
    country_code="+91",
):
    """
    Returns a normalized phone number.

    Examples

    9876543210
        ->
    +919876543210

    +919876543210
        ->
    +919876543210

    91 98765 43210
        ->
    +919876543210

    (987)-654-3210
        ->
    +919876543210
    """

    if not phone_number:

        raise ValidationError(
            "Phone number is required."
        )

    # --------------------------------------
    # Remove spaces and symbols
    # --------------------------------------

    phone = re.sub(

        r"\D",

        "",

        str(phone_number),

    )

    country = re.sub(

        r"\D",

        "",

        str(country_code),

    )

    # --------------------------------------
    # Remove duplicate country code
    # --------------------------------------

    if phone.startswith(country):

        phone = phone[len(country):]

    # --------------------------------------
    # Validate
    # --------------------------------------

    if len(phone) < 6:

        raise ValidationError(
            "Invalid phone number."
        )

    return f"+{country}{phone}"


# ----------------------------------------------------------
# Format Currency
# ----------------------------------------------------------

def format_currency(
    amount,
    restaurant=None,
):
    """
    Formats currency for display.

    Examples

    ₹250.00

    $125.50

    AED 55.00
    """

    amount = money(amount)

    symbol = "₹"

    if (

        restaurant is not None

        and

        restaurant.currency_symbol

    ):

        symbol = restaurant.currency_symbol

    return f"{symbol}{amount:,.2f}"


# ----------------------------------------------------------
# Validate Payment
# ----------------------------------------------------------

def validate_payment(
    payment,
):
    """
    Performs common payment validation.

    Raises ValidationError
    if payment cannot proceed.
    """

    if payment is None:

        raise ValidationError(
            "Payment not found."
        )

    if payment.amount <= Decimal("0.00"):

        raise ValidationError(
            "Invalid payment amount."
        )

    if not payment.restaurant:

        raise ValidationError(
            "Restaurant not found."
        )

    if not payment.order:

        raise ValidationError(
            "Order not found."
        )

    if refunded_amount(payment) >= payment.amount:
        raise ValidationError(
            "Payment has already been fully refunded."
        )

    if payment.status == "failed":

        raise ValidationError(
            "Payment has failed."
        )

    return True


# ==========================================================
# REFUND HELPERS
# Part 6
# ==========================================================

# ----------------------------------------------------------
# Validate Refund
# ----------------------------------------------------------

def validate_refund(
    payment,
    amount,
):
    """
    Validate whether a refund can be created.

    Raises ValidationError if invalid.
    """

    validate_payment(payment)

    amount = money(amount)

    if amount <= Decimal("0.00"):

        raise ValidationError(
            "Refund amount must be greater than zero."
        )

    remaining = calculate_remaining_refund(
        payment
    )

    if amount > remaining:

        raise ValidationError(
            (
                f"Maximum refundable amount is "
                f"{remaining}."
            )
        )

    return True


# ----------------------------------------------------------
# Remaining Refund
# ----------------------------------------------------------

def calculate_remaining_refund(
    payment,
):
    """
    Returns the remaining refundable amount.
    """

    refunded = refunded_amount(
        payment
    )

    remaining = (

        money(payment.amount)

        -

        refunded

    )

    if remaining < Decimal("0.00"):

        remaining = Decimal("0.00")

    return round_money(
        remaining
    )


# ----------------------------------------------------------
# Create Refund
# ----------------------------------------------------------

@transaction.atomic
def create_refund(
    payment,
    amount,
    reason,
):
    """
    Creates a refund record.

    Does NOT call Razorpay.

    The RefundAPIView will:

    1. Call Razorpay
    2. Receive refund_id
    3. Update this object
    """

    validate_refund(

        payment,

        amount,

    )

    refund = PaymentRefund.objects.create(

        payment=payment,

        amount=money(amount),

        reason=reason,

        status="pending",

    )

    return refund


# ----------------------------------------------------------
# Fetch Refund Status
# ----------------------------------------------------------

def fetch_refund_status(
    refund,
):
    """
    Returns refund status.

    Useful for:

    RefundStatusAPIView
    """

    return {

        "refund_id": refund.refund_id,

        "payment_id": str(
            refund.payment.id
        ),

        "amount": refund.amount,

        "status": refund.status,

        "reason": refund.reason,

        "created_at": refund.created_at,

    }


# ----------------------------------------------------------
# Update Refund Status
# ----------------------------------------------------------

@transaction.atomic
def update_refund_status(

    refund,

    status,

    refund_id=None,

    gateway_response=None,

    expected_status=None

):
    """
    Updates refund after Razorpay response.
    """

    refund.status = status

    if refund_id:

        refund.refund_id = refund_id

    if gateway_response is not None:

        refund.gateway_response = gateway_response

    refund.save(

        update_fields=[

            "status",

            "refund_id",

            "gateway_response",

        ]

    )

# ------------------------------------------
# Update Payment Status
# ------------------------------------------

    payment = refund.payment

    updated_fields = []

    if is_fully_refunded(payment):

        payment.status = "refunded"

    elif is_partially_refunded(payment):

        payment.status = "partially_refunded"

    else:

        payment.status = "paid"

    payment.save(
        update_fields=[
            "status",
        ]
    )


    if (
        expected_status == "paid"
        and
        payment.verified_at is None
    ):

        payment.verified_at = timezone.now()

        updated_fields.append(
            "verified_at"
        )

    

# ==========================================================
# RECONCILIATION HELPERS
# Part 7B1
# ==========================================================


# ----------------------------------------------------------
# Compare Gateway Payment
# ----------------------------------------------------------

"""
payments/services.py
Part 7B1 - Reconciliation Helpers

Requires existing helpers:
    money()
"""


def compare_gateway_payment(payment, gateway_payment):
    """
    Compare local PaymentTransaction with Razorpay payment.
    Returns reconciliation details.
    """
    changes = []

    if not gateway_payment:
        return {
            "matched": False,
            "change_count": 1,
            "changes": [{
                "field": "gateway",
                "error": "Gateway payment not found.",
            }],
            "gateway_status": None,
            "gateway_amount": Decimal("0.00"),
            "gateway_currency": None,
        }

    def normalize_status(status):
        status = (status or "").lower()
        mapping = {
            "created": "pending",
            "pending": "pending",
            "authorized": "authorized",
            "captured": "paid",
            "paid": "paid",
            "failed": "failed",
            "cancelled": "cancelled",
            "expired": "expired",
            "refunded": "refunded",
            "partially_refunded": "partially_refunded",
        }
        return mapping.get(status, status)

    gateway_status = normalize_status(gateway_payment.get("status"))

    gateway_amount = money(
        Decimal(str(gateway_payment.get("amount", 0))) / Decimal("100")
    )

    gateway_currency = (
        gateway_payment.get("currency", "") or ""
    ).upper()

    local_status = normalize_status(payment.status)
    local_amount = money(payment.amount)
    local_currency = (payment.currency or "").upper()

    if local_status != gateway_status:
        changes.append({
            "field": "status",
            "local": local_status,
            "gateway": gateway_status,
        })

    if local_amount != gateway_amount:
        changes.append({
            "field": "amount",
            "local": local_amount,
            "gateway": gateway_amount,
        })

    if local_currency != gateway_currency:
        changes.append({
            "field": "currency",
            "local": local_currency,
            "gateway": gateway_currency,
        })

    cached = payment.gateway_response or {}

    cached_status = normalize_status(cached.get("status"))
    cached_amount = cached.get("amount")
    cached_currency = (cached.get("currency") or "").upper()

    if cached_status != gateway_status:
        changes.append({
            "field": "gateway_response.status",
            "cached": cached_status,
            "gateway": gateway_status,
        })

    if cached_amount not in (None, ""):
        cached_amount = money(
            Decimal(str(cached_amount)) / Decimal("100")
        )
        if cached_amount != gateway_amount:
            changes.append({
                "field": "gateway_response.amount",
                "cached": cached_amount,
                "gateway": gateway_amount,
            })

    if cached_currency and cached_currency != gateway_currency:
        changes.append({
            "field": "gateway_response.currency",
            "cached": cached_currency,
            "gateway": gateway_currency,
        })

    return {
        "matched": len(changes) == 0,
        "change_count": len(changes),
        "changes": changes,
        "gateway_status": gateway_status,
        "gateway_amount": gateway_amount,
        "gateway_currency": gateway_currency,
    }


def compare_local_payment(payment):
    """
    Compare PaymentTransaction with linked Order.
    """
    changes = []
    order = payment.order

    if payment.status == "paid":
        expected_payment = "paid"
        expected_order = "confirmed"
    elif payment.status == "failed":
        expected_payment = "failed"
        expected_order = "pending"
    elif payment.status == "refunded":
        expected_payment = "refunded"
        expected_order = order.status
    elif payment.status == "partially_refunded":
        expected_payment = "paid"
        expected_order = order.status
    else:
        expected_payment = "pending"
        expected_order = order.status

    if order.payment_status != expected_payment:
        changes.append({
            "field": "payment_status",
            "order": order.payment_status,
            "expected": expected_payment,
        })

    if order.status != expected_order:
        changes.append({
            "field": "order_status",
            "order": order.status,
            "expected": expected_order,
        })

    if money(order.grand_total) != money(payment.amount):
        changes.append({
            "field": "amount",
            "order": money(order.grand_total),
            "payment": money(payment.amount),
        })

    if order.restaurant_id != payment.restaurant_id:
        changes.append({
            "field": "restaurant",
            "order": order.restaurant_id,
            "payment": payment.restaurant_id,
        })

    return {
        "matched": len(changes) == 0,
        "change_count": len(changes),
        "changes": changes,
    }


"""
payments/services.py
Part 7B2 - Reconciliation Helpers

Requires existing helpers:
    is_fully_refunded()
    is_partially_refunded()
"""


@transaction.atomic
def fix_payment_status(payment, gateway_payment):
    """
    Synchronize PaymentTransaction with gateway state.
    """

    if not gateway_payment:
        raise ValidationError("Gateway payment data is required.")

    updated_fields = []

    gateway_status = (gateway_payment.get("status") or "").lower()

    status_mapping = {
        "created": "pending",
        "authorized": "authorized",
        "captured": "paid",
        "paid": "paid",
        "failed": "failed",
        "cancelled": "cancelled",
        "expired": "expired",
        "refunded": "refunded",
    }

    expected_status = status_mapping.get(
        gateway_status,
        payment.status,
    )

    if is_fully_refunded(payment):
        expected_status = "refunded"
    elif is_partially_refunded(payment):
        expected_status = "partially_refunded"

    if expected_status == "paid" and payment.paid_at is None:
        payment.paid_at = timezone.now()
        updated_fields.append("paid_at")

    if expected_status == "paid" and getattr(payment, "verified_at", None) is None:
        payment.verified_at = timezone.now()
        updated_fields.append("verified_at")

    if payment.status != expected_status:
        payment.status = expected_status
        updated_fields.append("status")

    current_response = payment.gateway_response or {}
    if current_response != gateway_payment:
        payment.gateway_response = gateway_payment
        updated_fields.append("gateway_response")

    gateway_payment_id = gateway_payment.get("id")
    if gateway_payment_id and payment.gateway_payment_id != gateway_payment_id:
        payment.gateway_payment_id = gateway_payment_id
        updated_fields.append("gateway_payment_id")

    gateway_order_id = gateway_payment.get("order_id")
    if gateway_order_id and payment.gateway_order_id != gateway_order_id:
        payment.gateway_order_id = gateway_order_id
        updated_fields.append("gateway_order_id")

    if updated_fields:
        payment.save(update_fields=updated_fields)

    return {
        "updated": bool(updated_fields),
        "updated_fields": updated_fields,
        "payment_status": payment.status,
        "gateway_status": gateway_status,
    }


@transaction.atomic
def fix_order_status(payment):
    """
    Synchronize Order from PaymentTransaction.
    """

    order = payment.order
    updated_fields = []

    if payment.status == "paid":
        expected_payment = "paid"
        expected_order = "confirmed"
    elif payment.status == "failed":
        expected_payment = "failed"
        expected_order = "pending"
    elif payment.status == "refunded":
        expected_payment = "refunded"
        expected_order = order.status
    elif payment.status == "partially_refunded":
        expected_payment = "paid"
        expected_order = order.status
    else:
        expected_payment = "pending"
        expected_order = order.status

    if order.payment_status != expected_payment:
        order.payment_status = expected_payment
        updated_fields.append("payment_status")

    if order.status != expected_order:
        order.status = expected_order
        updated_fields.append("status")

    if updated_fields:
        order.save(update_fields=updated_fields)

    return {
        "updated": bool(updated_fields),
        "updated_fields": updated_fields,
        "order_status": order.status,
        "order_payment_status": order.payment_status,
    }

"""
payments/services.py
Part 5 - Utilities
"""

# ----------------------------------------------------------
# Normalize Phone Number
# ----------------------------------------------------------

def normalize_phone(phone_number, country_code="+91"):
    """
    Normalize a phone number into E.164 format.
    """

    if not phone_number:
        raise ValidationError("Phone number is required.")

    phone = re.sub(r"\D", "", str(phone_number))
    country = re.sub(r"\D", "", str(country_code))

    if phone.startswith(country):
        phone = phone[len(country):]

    if len(phone) < 6:
        raise ValidationError("Invalid phone number.")

    return f"+{country}{phone}"


# ----------------------------------------------------------
# Format Currency
# ----------------------------------------------------------

def format_currency(amount, restaurant=None):
    """
    Format a monetary amount using the restaurant currency.
    """

    amount = money(amount)

    symbol = "₹"

    if (
        restaurant is not None
        and getattr(restaurant, "currency_symbol", None)
    ):
        symbol = restaurant.currency_symbol

    return f"{symbol}{amount:,.2f}"


# ----------------------------------------------------------
# Validate Payment
# ----------------------------------------------------------

def validate_payment(payment):
    """
    Common validation before payment operations.

    Raises ValidationError on failure.
    """

    if payment is None:
        raise ValidationError("Payment not found.")

    if money(payment.amount) <= Decimal("0.00"):
        raise ValidationError("Invalid payment amount.")

    if not payment.restaurant:
        raise ValidationError("Restaurant not found.")

    if not payment.order:
        raise ValidationError("Order not found.")

    if payment.status == "failed":
        raise ValidationError("Payment has failed.")

    if is_fully_refunded(payment):
        raise ValidationError("Payment has already been fully refunded.")

    return True


# ==========================================================
# REFUND HELPERS
# Part 6A
# ==========================================================

# ----------------------------------------------------------
# Calculate Remaining Refund
# ----------------------------------------------------------

def calculate_remaining_refund(
    payment,
):
    """
    Calculate the remaining refundable amount.

    Example

    Payment Amount : 1000

    Refunded : 250

    Remaining : 750

    Returns
    -------
    Decimal
    """

    validate_payment(
        payment
    )

    refunded = refunded_amount(
        payment
    )

    remaining = (

        money(payment.amount)

        -

        refunded

    )

    if remaining < Decimal("0.00"):

        remaining = Decimal("0.00")

    return round_money(
        remaining
    )


# ==========================================================
# Check Fully Refunded
# ==========================================================

def is_fully_refunded(payment):
    """
    Returns whether the payment has been fully refunded.

    A payment is considered fully refunded when the total
    processed refund amount is greater than or equal to the
    original payment amount.

    Args:
        payment (PaymentTransaction)

    Returns:
        bool
    """

    refunded_amount = (

        PaymentRefund.objects.filter(

            payment=payment,

            status="processed",

        ).aggregate(

            total=models.Sum("amount")

        )["total"]

        or Decimal("0.00")

    )

    return refunded_amount >= payment.amount


# ==========================================================
# Check Partially Refunded
# ==========================================================

def is_partially_refunded(payment):
    """
    Returns True if the payment has been partially refunded.
    """

    remaining = calculate_remaining_refund(payment)

    return (
        remaining > Decimal("0.00")
        and remaining < payment.amount
    )


# ----------------------------------------------------------
# Validate Refund
# ----------------------------------------------------------

def validate_refund(
    payment,
    amount,
):
    """
    Validate whether a refund can be created.

    Raises
    ------
    ValidationError
    """

    validate_payment(
        payment
    )

    amount = money(
        amount
    )

    # ------------------------------------------
    # Positive Amount
    # ------------------------------------------

    if amount <= Decimal("0.00"):

        raise ValidationError(
            "Refund amount must be greater than zero."
        )

    # ------------------------------------------
    # Remaining Refund
    # ------------------------------------------

    remaining = calculate_remaining_refund(
        payment
    )

    if amount > remaining:

        raise ValidationError(

            (
                "Refund amount exceeds the "
                "remaining refundable amount "
                f"({remaining})."
            )

        )

    # ------------------------------------------
    # Fully Refunded
    # ------------------------------------------

    if is_fully_refunded(
        payment
    ):

        raise ValidationError(
            "Payment has already been fully refunded."
        )

    return True


"""
payments/services.py
Part 8A - Dashboard Helpers

Requires:
    PaymentTransaction model
    money()
"""

def filter_payments(
    queryset,
    restaurant=None,
    status=None,
    payment_method=None,
    start_date=None,
    end_date=None,
):
    """
    Apply common dashboard filters to a PaymentTransaction queryset.
    """

    if restaurant is not None:
        queryset = queryset.filter(
            restaurant=restaurant
        )

    if status:
        queryset = queryset.filter(
            status=status
        )

    if payment_method:
        queryset = queryset.filter(
            payment_method=payment_method
        )

    if start_date:
        queryset = queryset.filter(
            created_at__date__gte=start_date
        )

    if end_date:
        queryset = queryset.filter(
            created_at__date__lte=end_date
        )

    return queryset


def calculate_sales(queryset):
    """
    Calculate sales statistics from a filtered queryset.
    """

    paid = queryset.filter(
        status="paid"
    )

    summary = paid.aggregate(
        total_sales=Sum("amount"),
        total_orders=Count("id"),
    )

    total_sales = money(
        summary["total_sales"] or Decimal("0.00")
    )

    total_orders = summary["total_orders"] or 0

    average_sale = (
        money(total_sales / total_orders)
        if total_orders
        else Decimal("0.00")
    )

    cash_sales = money(
        paid.filter(
            payment_method="cash"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    online_sales = money(
        paid.filter(
            payment_method="online"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "average_sale": average_sale,
        "cash_sales": cash_sales,
        "online_sales": online_sales,
    }

"""
payments/services.py
Part 8B - Dashboard Helpers

Requires:
    PaymentRefund model
    money()
"""

def calculate_refunds(queryset):
    """
    Calculate refund statistics from a filtered PaymentTransaction queryset.
    """

    refunds = PaymentRefund.objects.filter(
        payment__in=queryset
    )

    summary = refunds.aggregate(
        total_refunds=Sum("amount"),
        refund_count=Count("id"),
    )

    total_refunds = money(
        summary["total_refunds"] or Decimal("0.00")
    )

    refund_count = summary["refund_count"] or 0

    successful_refunds = refunds.filter(
        status="processed"
    ).count()

    pending_refunds = refunds.filter(
        status__in=["pending", "processing"]
    ).count()

    failed_refunds = refunds.filter(
        status="failed"
    ).count()

    return {
        "total_refunds": total_refunds,
        "refund_count": refund_count,
        "successful_refunds": successful_refunds,
        "pending_refunds": pending_refunds,
        "failed_refunds": failed_refunds,
    }


def calculate_dashboard_statistics(queryset):
    """
    Build dashboard summary using calculate_sales()
    and calculate_refunds().
    """

    sales = calculate_sales(queryset)
    refunds = calculate_refunds(queryset)

    net_sales = money(
        sales["total_sales"] - refunds["total_refunds"]
    )

    return {
        "sales": sales,
        "refunds": refunds,
        "net_sales": net_sales,
        "total_transactions": queryset.count(),
        "paid_transactions": queryset.filter(
            status="paid"
        ).count(),
        "failed_transactions": queryset.filter(
            status="failed"
        ).count(),
        "pending_transactions": queryset.filter(
            status="pending"
        ).count(),
    }


"""
payments/services.py
Part 9A - Sales Reports

Requires:
    filter_payments()
    calculate_sales()
"""

from collections import OrderedDict
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncMonth


def daily_sales_report(
    queryset,
    restaurant=None,
    start_date=None,
    end_date=None,
):
    """
    Daily sales summary.
    """

    queryset = filter_payments(
        queryset=queryset,
        restaurant=restaurant,
        start_date=start_date,
        end_date=end_date,
    ).filter(status="paid")

    rows = (
        queryset
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total_sales=Sum("amount"),
            total_orders=Count("id"),
        )
        .order_by("day")
    )

    report = []

    grand_total = Decimal("0.00")
    total_orders = 0

    for row in rows:

        sales = money(row["total_sales"] or Decimal("0.00"))

        orders = row["total_orders"] or 0

        grand_total += sales
        total_orders += orders

        report.append({
            "date": row["day"],
            "sales": sales,
            "orders": orders,
            "average_sale": (
                money(sales / orders)
                if orders else Decimal("0.00")
            ),
        })

    return {
        "report": report,
        "summary": {
            "total_sales": money(grand_total),
            "total_orders": total_orders,
            "average_sale": (
                money(grand_total / total_orders)
                if total_orders else Decimal("0.00")
            ),
        },
    }


def monthly_sales_report(
    queryset,
    restaurant=None,
    start_date=None,
    end_date=None,
):
    """
    Monthly sales summary.
    """

    queryset = filter_payments(
        queryset=queryset,
        restaurant=restaurant,
        start_date=start_date,
        end_date=end_date,
    ).filter(status="paid")

    rows = (
        queryset
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total_sales=Sum("amount"),
            total_orders=Count("id"),
        )
        .order_by("month")
    )

    report = []

    grand_total = Decimal("0.00")
    total_orders = 0

    for row in rows:

        sales = money(row["total_sales"] or Decimal("0.00"))

        orders = row["total_orders"] or 0

        grand_total += sales
        total_orders += orders

        report.append({
            "month": row["month"],
            "sales": sales,
            "orders": orders,
            "average_sale": (
                money(sales / orders)
                if orders else Decimal("0.00")
            ),
        })

    return {
        "report": report,
        "summary": {
            "total_sales": money(grand_total),
            "total_orders": total_orders,
            "average_sale": (
                money(grand_total / total_orders)
                if total_orders else Decimal("0.00")
            ),
        },
    }


"""
payments/services.py
Part 9B - Summary Helpers

Requires:
    PaymentRefund
    money()
"""

def payment_method_summary(queryset):
    """
    Summarize paid payments by payment method.
    """

    rows = (
        queryset.filter(status="paid")
        .values("payment_method")
        .annotate(
            total_amount=Sum("amount"),
            total_transactions=Count("id"),
        )
        .order_by("payment_method")
    )

    summary = []

    for row in rows:
        summary.append({
            "payment_method": row["payment_method"] or "unknown",
            "total_amount": money(row["total_amount"] or Decimal("0.00")),
            "total_transactions": row["total_transactions"] or 0,
        })

    return summary


def refund_summary(queryset):
    """
    Summarize refunds for the supplied payments.
    """

    refunds = PaymentRefund.objects.filter(
        payment__in=queryset
    )

    rows = (
        refunds.values("status")
        .annotate(
            total_amount=Sum("amount"),
            total_refunds=Count("id"),
        )
        .order_by("status")
    )

    summary = []

    for row in rows:
        summary.append({
            "status": row["status"],
            "total_amount": money(row["total_amount"] or Decimal("0.00")),
            "total_refunds": row["total_refunds"] or 0,
        })

    return {
        "summary": summary,
        "grand_total": money(
            refunds.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")
        ),
    }


def tax_summary(queryset):
    """
    Summarize collected tax from paid payments.
    Assumes PaymentTransaction.tax_amount exists.
    """

    paid = queryset.filter(status="paid")

    total_tax = money(
        paid.aggregate(
            total=Sum("tax_amount")
        )["total"] or Decimal("0.00")
    )

    taxable_sales = money(
        paid.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    return {
        "taxable_sales": taxable_sales,
        "tax_collected": total_tax,
        "effective_tax_rate": (
            round(
                (total_tax / taxable_sales) * 100,
                2,
            )
            if taxable_sales
            else 0
        ),
    }


"""
payments/services.py
Part 9C - Analytics Helpers

Requires:
    OrderItem model related to Order as order_items
    money()
"""

from decimal import Decimal
from django.db.models import Sum, Count, F


def top_customers(queryset, limit=10):
    """
    Return top customers by paid sales.
    """

    rows = (
        queryset.filter(status="paid")
        .values(
            "customer_name",
            "customer_email",
        )
        .annotate(
            total_spent=Sum("amount"),
            total_orders=Count("id"),
        )
        .order_by("-total_spent")[:limit]
    )

    return [
        {
            "customer_name": row["customer_name"] or "Unknown",
            "customer_email": row["customer_email"] or "",
            "total_spent": money(row["total_spent"] or Decimal("0.00")),
            "total_orders": row["total_orders"] or 0,
        }
        for row in rows
    ]


def top_items(queryset, limit=10):
    """
    Return top selling items.

    Assumes:
        PaymentTransaction -> Order -> order_items
        OrderItem has:
            food_item
            quantity
            total_price
    """

    order_ids = queryset.filter(
        status="paid"
    ).values_list(
        "order_id",
        flat=True,
    )

    rows = (
        OrderItem.objects.filter(
            order_id__in=order_ids
        )
        .values(
            item_name=F("food_item__name"),
        )
        .annotate(
            quantity_sold=Sum("quantity"),
            revenue=Sum("total_price"),
        )
        .order_by("-quantity_sold")[:limit]
    )

    return [
        {
            "item_name": row["item_name"] or "Unknown",
            "quantity_sold": row["quantity_sold"] or 0,
            "revenue": money(row["revenue"] or Decimal("0.00")),
        }
        for row in rows
    ]


"""
payments/services.py
Part 9D - Export Helpers

Requires:
    daily_sales_report()
    openpyxl
"""

def export_sales_csv(queryset, restaurant=None, start_date=None, end_date=None):
    """
    Export daily sales report as CSV text.
    """

    report = daily_sales_report(
        queryset=queryset,
        restaurant=restaurant,
        start_date=start_date,
        end_date=end_date,
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Date",
        "Sales",
        "Orders",
        "Average Sale",
    ])

    for row in report["report"]:
        writer.writerow([
            row["date"],
            row["sales"],
            row["orders"],
            row["average_sale"],
        ])

    summary = report["summary"]

    writer.writerow([])
    writer.writerow(["Total Sales", summary["total_sales"]])
    writer.writerow(["Total Orders", summary["total_orders"]])
    writer.writerow(["Average Sale", summary["average_sale"]])

    return output.getvalue()


def export_sales_excel(queryset, restaurant=None, start_date=None, end_date=None):
    """
    Export daily sales report as an openpyxl Workbook.
    """

    report = daily_sales_report(
        queryset=queryset,
        restaurant=restaurant,
        start_date=start_date,
        end_date=end_date,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    ws.append([
        "Date",
        "Sales",
        "Orders",
        "Average Sale",
    ])

    for row in report["report"]:
        ws.append([
            str(row["date"]),
            float(row["sales"]),
            row["orders"],
            float(row["average_sale"]),
        ])

    ws.append([])

    summary = report["summary"]

    ws.append(["Total Sales", float(summary["total_sales"])])
    ws.append(["Total Orders", summary["total_orders"]])
    ws.append(["Average Sale", float(summary["average_sale"])])

    buffer = BytesIO()
    Workbook.save(buffer)
    buffer.seek(0)

    return wb


"""
payments/services.py
Part 10A - Core Validation Helpers
"""

from decimal import Decimal
from django.core.exceptions import ValidationError


# ----------------------------------------------------------
# Validate Order
# ----------------------------------------------------------

def validate_order(order):
    """
    Validate an Order before payment/receipt operations.
    """

    if order is None:
        raise ValidationError("Order not found.")

    if getattr(order, "is_deleted", False):
        raise ValidationError("Order has been deleted.")

    if not getattr(order, "restaurant", None):
        raise ValidationError("Order is not linked to a restaurant.")

    grand_total = getattr(order, "grand_total", Decimal("0.00"))

    if money(grand_total) <= Decimal("0.00"):
        raise ValidationError("Order total must be greater than zero.")

    return True


# ----------------------------------------------------------
# Validate Refund
# ----------------------------------------------------------

def validate_refund(payment, amount):
    """
    Validate whether a refund may be created.
    """

    validate_payment(payment)

    amount = money(amount)

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Refund amount must be greater than zero."
        )

    remaining = calculate_remaining_refund(payment)

    if amount > remaining:
        raise ValidationError(
            f"Refund amount exceeds remaining refundable amount ({remaining})."
        )

    if is_fully_refunded(payment):
        raise ValidationError(
            "Payment has already been fully refunded."
        )

    return True


# ----------------------------------------------------------
# Validate Receipt
# ----------------------------------------------------------

def validate_receipt(receipt):
    """
    Validate a receipt before emailing,
    WhatsApp delivery or download.
    """

    if receipt is None:
        raise ValidationError(
            "Receipt not found."
        )

    if not getattr(receipt, "payment", None):
        raise ValidationError(
            "Receipt is not linked to a payment."
        )

    if not receipt.invoice_number:
        raise ValidationError(
            "Invoice number is missing."
        )

    if not getattr(receipt, "restaurant", None):
        raise ValidationError(
            "Receipt is not linked to a restaurant."
        )

    payment = receipt.payment

    if payment.status not in (
        "paid",
        "partially_refunded",
        "refunded",
    ):
        raise ValidationError(
            "Receipt can only exist for completed payments."
        )

    return True


"""
payments/services.py
Part 10B - Configuration Validation Helpers

Requires:
    get_payment_settings()
"""

# ----------------------------------------------------------
# Validate Gateway Settings
# ----------------------------------------------------------

def validate_gateway_settings(settings_obj):
    """
    Validate payment gateway configuration.
    """

    if settings_obj is None:
        raise ValidationError(
            "Payment settings not found."
        )

    if not settings_obj.is_active:
        raise ValidationError(
            "Payments are disabled."
        )

    if not settings_obj.accept_online:
        raise ValidationError(
            "Online payments are disabled."
        )

    if not settings_obj.razorpay_key_id:
        raise ValidationError(
            "Razorpay Key ID is missing."
        )

    if not settings_obj.razorpay_key_secret:
        raise ValidationError(
            "Razorpay Key Secret is missing."
        )

    return True


# ----------------------------------------------------------
# Validate Restaurant Payment
# ----------------------------------------------------------

def validate_restaurant_payment(restaurant):
    """
    Validate that a restaurant can accept payments.
    """

    if restaurant is None:
        raise ValidationError(
            "Restaurant not found."
        )

    settings_obj = get_payment_settings(
        restaurant
    )

    validate_gateway_settings(
        settings_obj
    )

    if not getattr(restaurant, "tax_enabled", True):
        pass

    if not getattr(restaurant, "currency_symbol", None):
        raise ValidationError(
            "Restaurant currency is not configured."
        )

    return True


# ----------------------------------------------------------
# Validate Invoice
# ----------------------------------------------------------

def validate_invoice(receipt):
    """
    Validate invoice before PDF generation,
    download, email or WhatsApp delivery.
    """

    validate_receipt(receipt)

    payment = receipt.payment

    if payment.status not in (
        "paid",
        "partially_refunded",
        "refunded",
    ):
        raise ValidationError(
            "Invoice is only available for completed payments."
        )

    if not receipt.invoice_number:
        raise ValidationError(
            "Invoice number is missing."
        )

    if not receipt.invoice_date:
        raise ValidationError(
            "Invoice date is missing."
        )

    restaurant = receipt.restaurant

    if not getattr(restaurant, "invoice_prefix", None):
        raise ValidationError(
            "Restaurant invoice prefix is not configured."
        )

    if not getattr(restaurant, "name", None):
        raise ValidationError(
            "Restaurant name is missing."
        )

    return True
