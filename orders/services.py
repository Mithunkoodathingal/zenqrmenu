"""Placing orders and moving them through their statuses. Other parts (coupons, payments, stock, delivery,
notifications) hook in here so every status change applies the same rules."""
import hashlib
import secrets
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, ValidationError

from common.email import send_email
from restaurants.models import Branch, Restaurant, Table

from .models import Order, OrderEvent, OrderItem
from .pricing import _fail, parse_schedule, price_order

S = Order.Status
FLOW = [S.PENDING, S.CONFIRMED, S.PREPARING, S.READY, S.COMPLETED]


def _type(raw, table):
    t = str(raw or "").strip().lower().replace("-", "").replace("_", "")
    if not t:
        return Order.Type.DINEIN if table else Order.Type.PICKUP
    if t not in Order.Type.values:
        _fail("order_type", "Pick dine-in, pickup or delivery.")
    return t


def _resolve_place(data):
    table = None
    if data.get("table") not in (None, "", "null"):
        try:
            table = Table.objects.select_related("restaurant", "branch").get(pk=int(data["table"]))
        except (Table.DoesNotExist, TypeError, ValueError):
            _fail("table", "This table's QR code is no longer valid.")
        restaurant = table.restaurant
        if data.get("restaurant") not in (None, "") and str(data["restaurant"]) != str(restaurant.id):
            _fail("restaurant", "This table belongs to a different restaurant.")
    else:
        try:
            restaurant = Restaurant.objects.get(pk=int(data.get("restaurant") or 0))
        except (Restaurant.DoesNotExist, TypeError, ValueError):
            _fail("restaurant", "Restaurant not found.")
    if not restaurant.is_active or restaurant.deleted_at:
        _fail("restaurant", "This restaurant isn't taking orders.")
    if table:
        branch = table.branch
    elif data.get("branch") not in (None, ""):
        branch = Branch.objects.filter(restaurant=restaurant, pk=data.get("branch"), is_active=True).first()
        if branch is None:
            _fail("branch", "This branch isn't taking orders.")
    else:
        branch = restaurant.main_branch()
    if not branch.is_active:
        _fail("branch", "This branch isn't taking orders.")
    return restaurant, branch, table


def create_order(data, customer):
    restaurant, branch, table = _resolve_place(data)
    order_type = _type(data.get("order_type"), table)
    if order_type == Order.Type.DINEIN and table is None:
        _fail("table", "Scan the QR code on your table to order dine-in.")
    if order_type != Order.Type.DINEIN and table is not None:
        _fail("order_type", "Table QR codes are for dine-in. Use pickup or delivery ordering instead.")
    if order_type != Order.Type.DINEIN:
        if customer is None:
            raise NotAuthenticated("Sign in to place pickup or delivery orders.")
        if not customer.email_verified:
            _fail("customer", "Confirm your email before placing pickup or delivery orders.")
    if order_type == Order.Type.PICKUP and not restaurant.enable_pickup:
        _fail("order_type", f"{restaurant.name} isn't taking pickup orders.")
    if order_type == Order.Type.DELIVERY and not restaurant.enable_delivery:
        _fail("order_type", f"{restaurant.name} isn't delivering right now.")

    method = str(data.get("payment_method") or "cash").lower()
    if method not in Order.PaymentMethod.values:
        _fail("payment_method", "Pick cash or online payment.")
    scheduled = parse_schedule(restaurant, data.get("scheduled_time"), order_type)
    bill = price_order(restaurant, branch, order_type, data, customer, method)

    name = str(data.get("customer_name") or "").strip()[:150] or bill.get("address_name") or (customer.name if customer else "")
    phone = str(data.get("customer_phone") or "").strip()[:20] or bill.get("address_phone") or (customer.phone if customer else "")
    email = customer.email if customer else str(data.get("customer_email") or "").strip()[:254]
    if order_type == Order.Type.DELIVERY and not phone:
        _fail("customer_phone", "Add a phone number so the rider can reach you.")

    with transaction.atomic():
        Restaurant.objects.select_for_update().filter(pk=restaurant.pk).first()
        number = (Order.objects.filter(restaurant=restaurant).aggregate(n=Max("number"))["n"] or 0) + 1
        order = Order.objects.create(
            restaurant=restaurant, branch=branch, table=table, table_number=table.table_number if table else "",
            customer=customer, number=number, order_number=f"ZQ-{1000 + number}", order_type=order_type,
            customer_name=name, customer_phone=phone, customer_email=email,
            customer_note=str(data.get("customer_note") or data.get("delivery_instructions") or "").strip()[:1000],
            customer_address=bill.get("customer_address", ""), delivery_latitude=bill.get("delivery_latitude"),
            delivery_longitude=bill.get("delivery_longitude"), delivery_distance_km=bill.get("delivery_distance_km"),
            scheduled_time=scheduled, utensils_needed=bool(data.get("utensils_needed")) and order_type != Order.Type.DINEIN,
            tip_recipient=bill["tip_recipient"], subtotal=bill["subtotal"], discount_amount=bill["discount_amount"],
            coupon_code=bill["coupon_code"], online_discount=bill["online_discount"], tax_amount=bill["tax_amount"],
            delivery_charge=bill["delivery_charge"], tip_amount=bill["tip_amount"], total=bill["total"], payment_method=method,
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, food_item=l["food"], name=l["name"], base_price=l["base_price"],
                                                 unit_price=l["unit_price"], quantity=l["quantity"], addons=l["addons"])
                                       for l in bill["lines"]])
        OrderEvent.objects.create(order=order, status=S.PENDING)
        if bill["coupon"] is not None:
            from coupons.services import redeem
            redeem(bill["coupon"], order, bill["discount_amount"])
        _hook("on_order_created", order)
    return order


ALLOWED = {
    S.PENDING: {S.CONFIRMED, S.PREPARING, S.READY, S.COMPLETED, S.CANCELLED},
    S.CONFIRMED: {S.PREPARING, S.READY, S.COMPLETED, S.CANCELLED},
    S.PREPARING: {S.READY, S.COMPLETED, S.CANCELLED},
    S.READY: {S.COMPLETED, S.CANCELLED},
    S.COMPLETED: set(),
    S.CANCELLED: set(),
}

HOOK_APPS = ["inventory", "payments", "delivery", "notifications"]


def _hook(name, order, *args):
    for app in HOOK_APPS:
        if apps.is_installed(app):
            module = __import__(f"{app}.hooks", fromlist=[name])
            fn = getattr(module, name, None)
            if fn:
                fn(order, *args)


def set_status(order, status, note=""):
    """Move an order to `status`. Raises 400 for impossible moves; stock/payment hooks may refuse with 409."""
    status = str(status or "").lower()
    if status not in S.values:
        _fail("status", "Unknown status.")
    if status == order.status:
        return order
    if status not in ALLOWED[order.status]:
        _fail("status", f"A {order.get_status_display().lower()} order can't be changed to {status}.")
    if (order.payment_method == Order.PaymentMethod.ONLINE and order.payment_status != Order.PaymentStatus.PAID
            and status not in (S.CANCELLED,)):
        _fail("status", "This order is waiting for online payment.")
    if (status == S.COMPLETED and order.order_type != Order.Type.DINEIN and order.customer_email
            and (order.restaurant.settings or {}).get("require_handover_code") and not order.handover_verified_at):
        _fail("status", "Enter the customer's handover code before completing this order.")
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        old = locked.status
        _hook("on_status_change", locked, old, status)
        locked.status = status
        now = timezone.now()
        fields = ["status", "updated_at"]
        if status == S.COMPLETED:
            locked.completed_at = now
            fields.append("completed_at")
        if status == S.CANCELLED:
            locked.cancelled_at = now
            fields.append("cancelled_at")
            if apps.is_installed("coupons"):
                from coupons.services import release
                release(locked)
        locked.save(update_fields=fields)
        OrderEvent.objects.create(order=locked, status=status, note=note[:255])
        _hook("after_status_change", locked, old, status)
    if status == S.READY and locked.order_type != Order.Type.DINEIN and locked.customer_email:
        transaction.on_commit(lambda: send_handover_code(locked))
    return locked


# ─── Handover code (pickup & delivery) ────────────────────────────────────

CODE_HOURS = 24
CODE_TRIES = 5


def _hash(order, code):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{order.pk}:{code}".encode()).hexdigest()


def send_handover_code(order):
    """Email the diner a 4-digit code they show at pickup or give the rider. Email first; SMS comes later."""
    if order.order_type == Order.Type.DINEIN:
        _fail("order", "Dine-in orders don't need a handover code.")
    if not order.customer_email:
        _fail("order", "This order has no customer email to send a code to.")
    code = f"{secrets.randbelow(10000):04d}"
    order.handover_code_hash = _hash(order, code)
    order.handover_code_expires_at = timezone.now() + timedelta(hours=CODE_HOURS)
    order.handover_attempts = 0
    order.handover_verified_at = None
    order.save(update_fields=["handover_code_hash", "handover_code_expires_at", "handover_attempts", "handover_verified_at", "updated_at"])
    what = "pick up your order" if order.order_type == Order.Type.PICKUP else "receive your delivery"
    send_email(order.customer_email, f"Your handover code for order {order.order_number}",
               f"Hi {order.customer_name or 'there'},\n\nShow this code when you {what} from {order.restaurant.name}: {code}\n\n"
               f"It works for {CODE_HOURS} hours. Don't share it until you have your food.")
    return order.handover_code_expires_at


def verify_handover_code(order, code):
    if not order.handover_code_hash or not order.handover_code_expires_at:
        _fail("otp", "No handover code has been sent for this order yet.")
    if order.handover_verified_at:
        return True
    if timezone.now() > order.handover_code_expires_at or order.handover_attempts >= CODE_TRIES:
        _fail("otp", "This code has expired. Send a new one.")
    if not secrets.compare_digest(order.handover_code_hash, _hash(order, str(code or "").strip())):
        order.handover_attempts += 1
        order.save(update_fields=["handover_attempts"])
        _fail("otp", "Wrong code. Ask the customer to check their email.")
    order.handover_verified_at = timezone.now()
    order.save(update_fields=["handover_verified_at", "updated_at"])
    return True
