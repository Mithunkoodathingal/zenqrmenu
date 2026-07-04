"""
===============================================================================
Payment Order APIs

Handles:

    • Create Razorpay Order
    • Verify Razorpay Payment

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
    get_payment_settings,
    get_restaurant_client,
)

# =============================================================================
# Restaurant Helpers
# =============================================================================

from payments.services import get_restaurant

class CreateRazorpayOrderAPIView(APIView):

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

        settings_obj = get_payment_settings(
            restaurant
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

        amount = Decimal(order.total_price_cached)

        if amount <= 0:

            return Response(
                {
                    "success": False,
                    "message": "Invalid order amount."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = PaymentTransaction.objects.filter(

            order=order,

            status__in=[
                "created",
                "pending",
                "authorized",
            ]

        ).first()

        if existing:

            return Response(
                {
                    "success": True,
                    "transaction_id": str(existing.id),
                    "razorpay_order_id": existing.gateway_order_id,
                    "amount": float(existing.amount),
                    "currency": existing.currency,
                    "key": settings_obj.razorpay_key_id,
                }
            )

        razorpay_order = client.order.create(
            {
                "amount": int(amount * 100),
                "currency": settings_obj.currency,
                "receipt": str(order.order_number),
                "payment_capture": 1,
            }
        )

        payment = PaymentTransaction.objects.create(

            restaurant=restaurant,

            order=order,

            gateway="razorpay",

            payment_mode="online",

            source=order.order_type,

            status="created",

            amount=amount,

            currency=settings_obj.currency,

            gateway_order_id=razorpay_order["id"],

            customer_name=order.customer_name,

            customer_phone=order.customer_phone,

            customer_email=order.customer_email,

            gateway_response=razorpay_order,

        )

        order.payment_status = "pending"

        order.save(
            update_fields=[
                "payment_status",
            ]
        )

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="created",

            description="Razorpay order created.",

            request=request,

        )

        return Response(
            {
                "success": True,

                "transaction_id": str(payment.id),

                "razorpay_order_id": payment.gateway_order_id,

                "amount": int(amount * 100),

                "currency": payment.currency,

                "key": settings_obj.razorpay_key_id,
            }
        )
    

class VerifyPaymentAPIView(APIView):

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

        if payment.status == "paid":

            return Response(
                {
                    "success": True,
                    "message": "Payment already verified.",
                    "order_id": str(order.id),
                    "payment_id": str(payment.id),
                }
            )

        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")

        if not all([
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        ]):

            return Response(
                {
                    "success": False,
                    "message": "Missing payment details."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            client = get_restaurant_client(
                restaurant
            )

            if payment.gateway_order_id != razorpay_order_id:
                return Response(
                    {
                        "success": False,
                        "message": "Order ID mismatch."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
            

        except Exception as e:

            payment.status = "failed"

            payment.failure_reason = str(e)

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                ]
            )

            order.payment_status = "failed"
            order.save(update_fields=["payment_status"])

            create_audit_log(

                restaurant=restaurant,

                payment=payment,

                action="failed",

                description=str(e),

                request=request,

            )

            return Response(
                {
                    "success": False,
                    "message": "Payment verification failed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.status = "paid"

        payment.gateway_payment_id = razorpay_payment_id

        payment.gateway_signature = razorpay_signature

        payment.paid_at = timezone.now()

        payment.save(
            update_fields=[
                "status",
                "gateway_payment_id",
                "gateway_signature",
                "paid_at",
            ]
        )

        order.payment_status = "paid"
        order.status = "confirmed"

        order.save(
            update_fields=[
                "payment_status",
                "status",
            ]
        )

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="payment",

            description="Payment verified successfully.",

            request=request,

        )

        return Response(
            {
                "success": True,
                "message": "Payment verified successfully.",
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            }
        )