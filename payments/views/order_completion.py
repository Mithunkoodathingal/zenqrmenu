"""
===============================================================================
Order Completion APIs

Handles:

    • Complete Paid Orders
    • OTP Verification Checks
    • Audit Logging

===============================================================================
"""

# =============================================================================
# Django Imports
# =============================================================================

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

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
    PaymentTransaction,
)

from payments.services import (
    create_audit_log,
)

# =============================================================================
# Restaurant Helpers
# =============================================================================

from restaurant.services.common import get_restaurant


class CompleteOrderAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):

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
        )

        if payment.order_id != order.id:
            return Response(
                {
                    "success": False,
                    "message": "Invalid payment."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status != "paid":
            return Response(
                {
                    "success": False,
                    "message": "Payment not completed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pickup and Delivery require OTP
        if order.order_type in ["pickup", "delivery"]:

            if not payment.otp_verified:

                return Response(
                    {
                        "success": False,
                        "message": "OTP verification pending."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Prevent completing an already completed order
        if order.status == "completed":

            return Response(
                {
                    "success": False,
                    "message": "Order already completed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status == "cancelled":

            return Response(
                {
                    "success": False,
                    "message": "Cancelled orders cannot be completed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = "completed"

        order.is_completed = True

        order.completed_at = timezone.now()

        order.payment_status = "paid"

        if order.order_type == "delivery":
            order.delivery_verified = True

        order.save(
            update_fields=[
                "status",
                "is_completed",
                "completed_at",
                "payment_status",
                "delivery_verified",
            ]
        )

        create_audit_log(
            restaurant=restaurant,
            payment=payment,
            action="payment",
            description="Order completed.",
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": "Order completed successfully."
            }
        )
        
