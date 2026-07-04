#------payments/receipt.py------#

import os
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
import mimetypes
import requests

from django.conf import settings


def generate_receipt_pdf(receipt):
    """
    Generate invoice PDF using WeasyPrint.

    Parameters
    ----------
    receipt : Receipt

    Returns
    -------
    bytes
        Generated PDF bytes.

    Raises
    ------
    Exception
        If PDF generation fails.
    """

    payment = receipt.payment
    order = payment.order
    restaurant = payment.restaurant

    # ==========================================
    # Order Items
    # ==========================================

    items = (
        order.order_items
        .select_related("food_item")
        .prefetch_related("selected_addons")
    )

    # ==========================================
    # Calculate Subtotal
    # ==========================================

    subtotal = Decimal("0.00")

    for item in items:

        food_price = (
            item.food_item.price
            or Decimal("0.00")
        )

        subtotal += (
            food_price * item.quantity
        )

        addons_total = Decimal("0.00")

        for addon in item.selected_addons.all():

            addons_total += (
                addon.price
                or Decimal("0.00")
            )

        subtotal += (
            addons_total * item.quantity
        )

    # ==========================================
    # Other Charges
    # ==========================================

    discount = getattr(
        order,
        "discount_amount",
        Decimal("0.00"),
    )

    delivery_charge = getattr(
        order,
        "delivery_charge",
        Decimal("0.00"),
    )

    tax = getattr(
        order,
        "tax_amount",
        Decimal("0.00"),
    )

    grand_total = payment.amount

    # ==========================================
    # Template Context
    # ==========================================

    context = {

        "receipt": receipt,

        "restaurant": restaurant,

        "payment": payment,

        "order": order,

        "items": items,

        "subtotal": subtotal,

        "discount": discount,

        "delivery_charge": delivery_charge,

        "tax": tax,

        "grand_total": grand_total,

        "generated_at": timezone.now(),

    }

    # ==========================================
    # Render HTML
    # ==========================================

    html = render_to_string(

        "receipts/invoice.html",

        context,

    )

    # ==========================================
    # Generate PDF
    # ==========================================

    pdf = HTML(

        string=html,

        base_url=settings.BASE_DIR,

    ).write_pdf()

    # ==========================================
    # Save PDF
    # ==========================================

    filename = (
        f"Invoice-{receipt.invoice_number}.pdf"
    )

    receipt.pdf.save(

        filename,

        ContentFile(pdf),

        save=False,

    )

    receipt.save(
        update_fields=[
            "pdf",
        ]
    )

    return pdf

def upload_whatsapp_media(receipt):
    """
    Upload a receipt PDF to WhatsApp Cloud API.

    Returns:
        media_id (str)
    Raises:
        Exception on failure.
    """

    # Generate PDF if missing
    if not receipt.pdf:
        generate_receipt_pdf(receipt)

    receipt.pdf.open("rb")

    try:
        filename = (
            f"Invoice-{receipt.invoice_number}.pdf"
        )

        content_type = (
            mimetypes.guess_type(filename)[0]
            or "application/pdf"
        )

        url = (
            f"https://graph.facebook.com/"
            f"{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
        )

        headers = {
            "Authorization":
                f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        }

        files = {
            "file": (
                filename,
                receipt.pdf,
                content_type,
            ),
        }

        data = {
            "messaging_product": "whatsapp",
        }

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=30,
        )

    finally:
        receipt.pdf.close()

    if response.status_code not in (200, 201):

        raise Exception(
            f"WhatsApp media upload failed: "
            f"{response.status_code} - {response.text}"
        )

    result = response.json()

    media_id = result.get("id")

    if not media_id:

        raise Exception(
            "WhatsApp did not return a media ID."
        )

    return media_id

def send_whatsapp_document(
    phone_number,
    media_id,
    receipt,
):
    """
    Sends an uploaded PDF document using
    WhatsApp Cloud API.

    Returns:
        WhatsApp API response JSON
    Raises:
        Exception on failure.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {

        "Authorization":
            f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",

        "Content-Type":
            "application/json",

    }

    payload = {

        "messaging_product": "whatsapp",

        "recipient_type": "individual",

        "to": phone_number,

        "type": "document",

        "document": {

            "id": media_id,

            "filename":
                f"Invoice-{receipt.invoice_number}.pdf",

            "caption":
                (
                    f"Thank you for your order.\n"
                    f"Invoice #{receipt.invoice_number}"
                ),

        },

    }

    response = requests.post(

        url,

        headers=headers,

        json=payload,

        timeout=30,

    )

    if response.status_code not in (200, 201):

        raise Exception(
            f"WhatsApp send failed: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()