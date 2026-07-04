"""
===============================================================================
Receipt APIs

Handles:

    • Generate Receipt PDF
    • Download Receipt PDF
    • Email Receipt

===============================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================

import logging
import os
from decimal import Decimal

# =============================================================================
# Django Imports
# =============================================================================

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone

# =============================================================================
# Django REST Framework Imports
# =============================================================================

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# =============================================================================
# Third-Party Imports
# =============================================================================

# from weasyprint import HTML

# =============================================================================
# Local Application Imports
# =============================================================================

from payments.receipt import send_whatsapp_document, upload_whatsapp_media
from restaurant.models import Order

from payments.models import (
    PaymentTransaction,
    Receipt,
)

from payments.services import (
    create_audit_log,
)

from payments.services import get_restaurant

# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Generate Receipt PDF
# ==========================================================

def generate_receipt_pdf(receipt):

    """
    Generates the invoice PDF using WeasyPrint.

    Returns:

        pdf_bytes,
        relative_file_path
    """
    
    from weasyprint import HTML
    
    
    payment = receipt.payment

    order = payment.order

    restaurant = payment.restaurant

    items = order.order_items.select_related(
        "food_item"
    ).prefetch_related(
        "selected_addons"
    )

    # ==========================================
    # Subtotal
    # ==========================================

    subtotal = Decimal("0.00")

    for item in items:

        base_price = (
            item.food_item.price
            or Decimal("0.00")
        )

        subtotal += (
            base_price * item.quantity
        )

        addon_total = sum(

            (
                addon.price
                or Decimal("0.00")
            )

            for addon in item.selected_addons.all()

        )

        subtotal += (
            addon_total * item.quantity
        )

    # ==========================================
    # Template Context
    # ==========================================

    context = {

        "receipt": receipt,

        "payment": payment,

        "order": order,

        "restaurant": restaurant,

        "items": items,

        "subtotal": subtotal,

        "tax": getattr(
            order,
            "tax_amount",
            Decimal("0.00")
        ),

        "discount": getattr(
            order,
            "discount_amount",
            Decimal("0.00")
        ),

        "delivery_charge": getattr(
            order,
            "delivery_charge",
            Decimal("0.00")
        ),

        "grand_total": payment.amount,

        "generated_at": timezone.now(),

        "BRAND_NAME": settings.BRAND_NAME,

        "BRAND_URL": settings.BRAND_URL,

    }

    # ==========================================
    # HTML
    # ==========================================

    html_string = render_to_string(

        "receipts/invoice.html",

        context,

    )

    # ==========================================
    # PDF
    # ==========================================

    pdf_bytes = HTML(

        string=html_string,

        base_url=settings.STATIC_ROOT or settings.BASE_DIR,

    ).write_pdf()

    # ==========================================
    # Filename
    # ==========================================

    filename = (

        f"INV-"

        f"{receipt.invoice_number}.pdf"

    )

    relative_path = os.path.join(

        "receipts",

        filename,

    )

    # ==========================================
    # Save File
    # ==========================================

    receipt.pdf.save(

        filename,

        ContentFile(pdf_bytes),

        save=False,

    )

    receipt.save(
        update_fields=[
            "pdf",
        ]
    )

    return pdf_bytes, relative_path


# ==========================================================
# Receipt PDF API
# ==========================================================

class ReceiptPDFAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):

        # ==========================================
        # Restaurant
        # ==========================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================
        # Order
        # ==========================================

        order = get_object_or_404(

            Order,

            id=order_id,

            restaurant=restaurant,

        )

        # ==========================================
        # Payment
        # ==========================================

        payment = get_object_or_404(

            PaymentTransaction,

            order=order,

            restaurant=restaurant,

        )

        # ==========================================
        # Receipt
        # ==========================================

        receipt = get_object_or_404(

            Receipt,

            payment=payment,

        )

        # ==========================================
        # Generate PDF if missing
        # ==========================================

        try:

            if not receipt.pdf:

                pdf_bytes, _ = generate_receipt_pdf(
                    receipt
                )

            else:

                receipt.pdf.open("rb")

                pdf_bytes = receipt.pdf.read()

                receipt.pdf.close()

        except Exception as e:

            logger.exception(e)

            return Response(
                {
                    "success": False,
                    "message": "Unable to generate receipt.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==========================================
        # Update Download Stats
        # ==========================================

        receipt.download_count += 1

        receipt.last_downloaded_at = timezone.now()

        receipt.save(
            update_fields=[
                "download_count",
                "last_downloaded_at",
            ]
        )

        # ==========================================
        # Audit Log
        # ==========================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="receipt",

            description=(
                f"Receipt downloaded "
                f"(Download #{receipt.download_count})"
            ),

            request=request,

        )

        # ==========================================
        # Response
        # ==========================================

        filename = (

            f"Invoice-"

            f"{receipt.invoice_number}.pdf"

        )

        response = HttpResponse(

            pdf_bytes,

            content_type="application/pdf",

        )

        response[
            "Content-Disposition"
        ] = (

            f'attachment; filename="{filename}"'

        )

        response[
            "Content-Length"
        ] = len(pdf_bytes)

        return response
    

class EmailReceiptAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        # ==========================================
        # Restaurant
        # ==========================================

        restaurant = get_restaurant(request)

        if restaurant is None:
            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================
        # Order
        # ==========================================

        order = get_object_or_404(
            Order,
            id=order_id,
            restaurant=restaurant,
        )

        # ==========================================
        # Payment
        # ==========================================

        payment = get_object_or_404(
            PaymentTransaction,
            order=order,
            restaurant=restaurant,
        )

        # ==========================================
        # Receipt
        # ==========================================

        receipt = get_object_or_404(
            Receipt,
            payment=payment,
        )

        # ==========================================
        # Customer Email
        # ==========================================

        customer_email = payment.customer_email

        if not customer_email:
            return Response(
                {
                    "success": False,
                    "message": "Customer email not available."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Generate PDF
        # ==========================================

        try:

            if not receipt.pdf:

                pdf_bytes = generate_receipt_pdf(
                    receipt
                )

            else:

                receipt.pdf.open("rb")

                pdf_bytes = receipt.pdf.read()

                receipt.pdf.close()

        except Exception as e:

            logger.exception(e)

            return Response(
                {
                    "success": False,
                    "message": "Unable to generate receipt PDF.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==========================================
        # Email Templates
        # ==========================================

        subject = f"Invoice {receipt.invoice_number}"

        context = {
            "restaurant": restaurant,
            "payment": payment,
            "receipt": receipt,
            "order": order,
            "BRAND_NAME": settings.BRAND_NAME,
            "BRAND_URL": settings.BRAND_URL,
        }

        text_body = render_to_string(
            "emails/receipt.txt",
            context,
        )

        html_body = render_to_string(
            "emails/receipt.html",
            context,
        )

        filename = (
            f"Invoice-{receipt.invoice_number}.pdf"
        )

        # ==========================================
        # Email Object
        # ==========================================

        email = EmailMultiAlternatives(

            subject=subject,

            body=text_body,

            from_email=settings.DEFAULT_FROM_EMAIL,

            to=[customer_email],

        )

        email.attach_alternative(

            html_body,

            "text/html",

        )

        email.attach(

            filename,

            pdf_bytes,

            "application/pdf",

        )

        # ==========================================
        # Send Email
        # ==========================================

        try:

            email.send(
                fail_silently=False
            )

        except Exception as e:

            logger.exception(e)

            create_audit_log(

                restaurant=restaurant,

                payment=payment,

                action="email_failed",

                description=str(e),

                request=request,

            )

            return Response(
                {
                    "success": False,
                    "message": "Unable to send receipt email.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==========================================
        # Update Receipt
        # ==========================================

        receipt.email_sent = True

        receipt.email_sent_at = timezone.now()

        receipt.save(
            update_fields=[
                "email_sent",
                "email_sent_at",
            ]
        )

        # ==========================================
        # Audit Log
        # ==========================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="email",

            description=f"Receipt emailed to {customer_email}",

            request=request,

        )

        # ==========================================
        # Response
        # ==========================================

        return Response(

            {

                "success": True,

                "message": "Receipt emailed successfully.",

                "invoice_number": receipt.invoice_number,

                "customer_email": customer_email,

                "email_sent_at": receipt.email_sent_at,

            },

            status=status.HTTP_200_OK,

        )


class ReceiptAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        order = get_object_or_404(

            Order,

            id=order_id,

            restaurant=restaurant,

        )

        payment = get_object_or_404(

            PaymentTransaction,

            order=order,

            restaurant=restaurant,

        )

        items = order.order_items.select_related(
            "food_item"
        ).prefetch_related(
            "selected_addons"
        )

        subtotal = Decimal("0.00")

        for item in items:

            subtotal += (
                (item.food_item.price or Decimal("0.00"))
                * item.quantity
            )

            subtotal += (
                sum(
                    addon.price or Decimal("0.00")
                    for addon in item.selected_addons.all()
                ) * item.quantity
            )

        context = {

            "restaurant": restaurant,

            "order": order,

            "payment": payment,

            "items": items,

            "subtotal": subtotal,

            "tax": order.tax_amount,

            "discount": order.discount_amount,

            "total": order.total_price_cached,

            "BRAND_NAME": settings.BRAND_NAME,
    
            "BRAND_URL": settings.BRAND_URL,

            "generated_at": timezone.now(),

        }

        return render(

            request,

            "receipts/invoice.html",

            context,

        )
        
        
class WhatsAppReceiptAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        # ==========================================
        # Restaurant
        # ==========================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================
        # Order
        # ==========================================

        order = get_object_or_404(

            Order,

            id=order_id,

            restaurant=restaurant,

        )

        # ==========================================
        # Payment
        # ==========================================

        payment = get_object_or_404(

            PaymentTransaction,

            order=order,

            restaurant=restaurant,

        )

        # ==========================================
        # Receipt
        # ==========================================

        receipt = get_object_or_404(

            Receipt,

            payment=payment,

        )

        # ==========================================
        # Customer Phone
        # ==========================================

        phone_number = payment.whatsapp_number

        if not phone_number:

            return Response(
                {
                    "success": False,
                    "message": "Customer phone number not available."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Normalize Phone Number
        # ==========================================

        # phone_number = (
        #     phone_number
        #     .replace(" ", "")
        #     .replace("-", "")
        #     .replace("+", "")
        # )

        # ==========================================
        # Upload & Send
        # ==========================================

        try:

            media_id = upload_whatsapp_media(
                receipt
            )

            whatsapp_response = send_whatsapp_document(

                phone_number=phone_number,

                media_id=media_id,

                receipt=receipt,

            )

        except Exception as e:

            logger.exception(e)

            create_audit_log(

                restaurant=restaurant,

                payment=payment,

                action="whatsapp_failed",

                description=str(e),

                request=request,

            )

            return Response(
                {
                    "success": False,
                    "message": "Unable to send WhatsApp receipt.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==========================================
        # Update Receipt
        # ==========================================

        receipt.whatsapp_sent = True

        receipt.whatsapp_sent_at = timezone.now()

        receipt.save(
            update_fields=[
                "whatsapp_sent",
                "whatsapp_sent_at",
            ]
        )

        # ==========================================
        # Audit Log
        # ==========================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="whatsapp",

            description=(
                f"Receipt sent to WhatsApp "
                f"{phone_number}"
            ),

            request=request,

        )

        # ==========================================
        # Response
        # ==========================================

        return Response(

            {

                "success": True,

                "message": "Receipt sent successfully via WhatsApp.",

                "invoice_number": receipt.invoice_number,

                "phone_number": phone_number,

                "sent_at": receipt.whatsapp_sent_at,

                "whatsapp_response": whatsapp_response,

            },

            status=status.HTTP_200_OK,

        )