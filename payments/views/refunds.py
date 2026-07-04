"""
===============================================================================
Refund APIs

Handles:

    • Create Refund
    • Refund Status
    • Razorpay Refund Processing

===============================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================

from decimal import Decimal

# =============================================================================
# Django Imports
# =============================================================================

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.shortcuts import get_object_or_404

# =============================================================================
# Django REST Framework Imports
# =============================================================================

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# =============================================================================
# Local Application Imports
# =============================================================================

from restaurant.models import Order

from payments.models import (
    PaymentRefund,
    PaymentTransaction,
)

from payments.services import (
    create_audit_log,
    get_restaurant_client,
)

from restaurant.integrations import get_restaurant


class RefundAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
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
        # Payment must be paid
        # ==========================================

        if payment.status != "paid":

            return Response(
                {
                    "success": False,
                    "message": "Only paid transactions can be refunded."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Gateway Payment ID required
        # ==========================================

        if not payment.gateway_payment_id:

            return Response(
                {
                    "success": False,
                    "message": "Gateway payment ID not found."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Refund Amount
        # ==========================================

        amount = request.data.get("amount")

        if amount in [None, ""]:

            refund_amount = payment.amount

        else:

            try:

                refund_amount = Decimal(amount)

            except Exception:

                return Response(
                    {
                        "success": False,
                        "message": "Invalid refund amount."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ==========================================
        # Amount Validation
        # ==========================================

        if refund_amount <= Decimal("0.00"):

            return Response(
                {
                    "success": False,
                    "message": "Refund amount must be greater than zero."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if refund_amount > payment.amount:

            return Response(
                {
                    "success": False,
                    "message": "Refund exceeds paid amount."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Refund Reason
        # ==========================================

        reason = request.data.get(
            "reason",
            "Requested by restaurant"
        )

        # ==========================================
        # Already Fully Refunded?
        # ==========================================

        if payment.status == "refunded":

            return Response(
                {
                    "success": False,
                    "message": "Payment already refunded."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Existing Refund Total
        # ==========================================

        previous_refunds = PaymentRefund.objects.filter(

            payment=payment,

            status="processed",

        )

        refunded_amount = sum(

            r.amount for r in previous_refunds

        )

        remaining_amount = payment.amount - refunded_amount

        if refund_amount > remaining_amount:

            return Response(
                {
                    "success": False,
                    "message": (
                        f"Maximum refundable amount is "
                        f"{remaining_amount}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Razorpay Client
        # ==========================================

        try:

            client = get_restaurant_client(
                restaurant
            )

        except ValidationError as e:

            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ======================================================
        # Part A2 starts here
        #
        # Next section will:
        #
        # • Call Razorpay Refund API
        # • Create PaymentRefund
        # • Update PaymentTransaction
        # • Update Order
        # • Create Audit Log
        # • Return Response
        # ======================================================

        # ==========================================
        # Create Razorpay Refund
        # ==========================================

        try:

            refund_response = client.payment.refund(

                payment.gateway_payment_id,

                {
                    "amount": int(refund_amount * 100),
                    "speed": "normal",
                    "notes": {
                        "order_id": str(order.id),
                        "transaction": payment.transaction_number,
                        "restaurant": restaurant.name,
                        "reason": reason,
                    },
                },

            )

        except Exception as e:

            create_audit_log(

                restaurant=restaurant,

                payment=payment,

                action="failed",

                description=f"Refund failed : {str(e)}",

                request=request,

            )

            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================
        # Save Refund
        # ==========================================

        refund = PaymentRefund.objects.create(

            payment=payment,

            refund_id=refund_response.get("id", ""),

            amount=refund_amount,

            reason=reason,

            status="processed",

            gateway_response=refund_response,

        )

        # ==========================================
        # Calculate Total Refunded
        # ==========================================

        total_refunded = PaymentRefund.objects.filter(

            payment=payment,

            status="processed",

        ).aggregate(

            total=models.Sum("amount")

        )["total"] or Decimal("0.00")

        # ==========================================
        # Update Payment Status
        # ==========================================

        if total_refunded >= payment.amount:

            payment.status = "refunded"

        else:

            payment.status = "partially_refunded"

        payment.gateway_response = refund_response

        payment.save(
            update_fields=[
                "status",
                "gateway_response",
            ]
        )

        # ==========================================
        # Update Order
        # ==========================================

        if payment.status == "refunded":

            order.payment_status = "refunded"

        else:

            order.payment_status = "partially_refunded"

        order.save(
            update_fields=[
                "payment_status",
                "status",
            ]
        )

        # ==========================================
        # Audit Log
        # ==========================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="refund",

            description=(
                f"Refunded ₹{refund_amount} "
                f"(Refund ID: {refund.refund_id})"
            ),

            request=request,

        )

        # ==========================================
        # Response
        # ==========================================

        return Response(
            {
                "success": True,

                "message": "Refund processed successfully.",

                "refund": {

                    "id": str(refund.id),

                    "refund_id": refund.refund_id,

                    "amount": float(refund.amount),

                    "status": refund.status,

                    "reason": refund.reason,

                    "created_at": refund.created_at,

                },

                "payment_status": payment.status,

                "order_payment_status": order.payment_status,

            },
            status=status.HTTP_200_OK,
        )
    

class RefundStatusAPIView(APIView):

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

        refund = PaymentRefund.objects.filter(

            payment=payment

        ).order_by(

            "-created_at"

        ).first()

        if refund is None:

            return Response(
                {
                    "success": False,
                    "message": "Refund not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:

            client = get_restaurant_client(
                restaurant
            )

        except ValidationError as e:

            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            gateway_refund = client.refund.fetch(
                refund.refund_id
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        gateway_status = gateway_refund.get(
            "status",
            "pending"
        )

        # ==========================================
        # Update Refund
        # ==========================================

        refund.gateway_response = gateway_refund

        if gateway_status == "processed":

            refund.status = "processed"

        elif gateway_status == "failed":

            refund.status = "failed"

        else:

            refund.status = "pending"

        refund.save(
            update_fields=[
                "status",
                "gateway_response",
            ]
        )

        # ==========================================
        # Update Payment
        # ==========================================

        processed_total = PaymentRefund.objects.filter(

            payment=payment,

            status="processed",

        ).aggregate(

            total=models.Sum("amount")

        )["total"] or Decimal("0.00")

        if processed_total == Decimal("0.00"):

            payment.status = "paid"

        elif processed_total < payment.amount:

            payment.status = "partially_refunded"

        else:

            payment.status = "refunded"

        payment.save(
            update_fields=[
                "status",
            ]
        )

        # ==========================================
        # Audit
        # ==========================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="refund",

            description=(
                f"Refund status checked "
                f"({refund.status})"
            ),

            request=request,

        )

        return Response(
            {

                "success": True,

                "refund": {

                    "id": str(refund.id),

                    "refund_id": refund.refund_id,

                    "status": refund.status,

                    "amount": refund.amount,

                    "reason": refund.reason,

                    "created_at": refund.created_at,

                },

                "payment_status": payment.status,

            }
        )