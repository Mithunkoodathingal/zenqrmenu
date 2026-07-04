
"""
===============================================================================
Payment History APIs

Payment History
Payment Details
Receipt PDF Generation

===============================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================

import os
from decimal import Decimal

# =============================================================================
# Django Imports
# =============================================================================

from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
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

from weasyprint import HTML

# =============================================================================
# Local Application Imports
# =============================================================================

from payments.models import (
    PaymentAuditLog,
    PaymentRefund,
    PaymentTransaction,
    Receipt,
)

from payments.serializers import (
    PaymentAuditLogSerializer,
    PaymentRefundSerializer,
    PaymentTransactionSerializer,
    ReceiptSerializer,
)

# =============================================================================
# Restaurant Helpers
# =============================================================================

from restaurant.integrations import get_restaurant

# ==========================================================
# Payment History API
# ==========================================================

class PaymentHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = PaymentTransaction.objects.filter(

            restaurant=restaurant

        ).select_related(

            "order"

        ).order_by(

            "-created_at"

        )

        # =====================================
        # Status Filter
        # =====================================

        payment_status = request.GET.get("status")

        if payment_status:

            queryset = queryset.filter(
                status=payment_status
            )

        # =====================================
        # Gateway Filter
        # =====================================

        gateway = request.GET.get("gateway")

        if gateway:

            queryset = queryset.filter(
                gateway=gateway
            )

        # =====================================
        # Payment Method Filter
        # =====================================

        method = request.GET.get("method")

        if method:

            queryset = queryset.filter(
                payment_method=method
            )

        # =====================================
        # Customer Search
        # =====================================

        customer = request.GET.get("customer")

        if customer:

            queryset = queryset.filter(

                customer_name__icontains=customer

            )

        # =====================================
        # Date Filter
        # =====================================

        start_date = request.GET.get("start_date")

        end_date = request.GET.get("end_date")

        if start_date:

            queryset = queryset.filter(

                created_at__date__gte=start_date

            )

        if end_date:

            queryset = queryset.filter(

                created_at__date__lte=end_date

            )

        serializer = PaymentTransactionSerializer(

            queryset,

            many=True,

        )

        return Response(

            {

                "success": True,

                "count": queryset.count(),

                "payments": serializer.data,

            }

        )
    

# ==========================================================
# Payment Detail API
# ==========================================================

class PaymentDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        payment = get_object_or_404(

            PaymentTransaction,

            id=payment_id,

            restaurant=restaurant,

        )

        refunds = PaymentRefund.objects.filter(

            payment=payment

        ).order_by(

            "-created_at"

        )

        receipt = Receipt.objects.filter(

            payment=payment

        ).first()

        audit_logs = PaymentAuditLog.objects.filter(

            payment=payment

        ).order_by(

            "-created_at"

        )

        return Response(

            {

                "success": True,

                "payment": PaymentTransactionSerializer(
                    payment
                ).data,

                "refunds": PaymentRefundSerializer(
                    refunds,
                    many=True,
                ).data,

                "receipt": (

                    ReceiptSerializer(receipt).data

                    if receipt

                    else None

                ),

                "audit_logs": PaymentAuditLogSerializer(

                    audit_logs,

                    many=True,

                ).data,

            }

        )
    
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

