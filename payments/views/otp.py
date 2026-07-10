"""
===============================================================================
OTP APIs

Handles:

    • Generate Completion OTP
    • Verify Completion OTP

===============================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================

import random
from datetime import timedelta

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


class GenerateOTPAPIView(APIView):

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

        
        if order.order_type == "dinein":

            return Response(
                {
                    "success": False,
                    "message": "OTP is not required for dine-in orders."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = get_object_or_404(

            PaymentTransaction,

            order=order,

            restaurant=restaurant,

        )

        if payment.status != "paid":

            return Response(
                {
                    "success": False,
                    "message": "Payment not completed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if payment.otp_verified:

            return Response(
                {
                    "success": False,
                    "message": "OTP already verified."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = f"{random.randint(100000, 999999)}"

        payment.otp_verified = False

        payment.otp_verified_at = None

        payment.completion_otp = otp

        payment.otp_expires_at = timezone.now() + timedelta(
            minutes=15
        )

        payment.save(
            update_fields=[
                "completion_otp",
                "otp_verified",
                "otp_verified_at",
                "otp_expires_at",
            ]
        )

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="updated",

            description="Completion OTP generated.",

            request=request,

        )

        return Response(
            {
                "success": True,
                "message": "OTP generated successfully.",
                "expires_at": payment.otp_expires_at,
            }
        )
    
class VerifyOTPAPIView(APIView):

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

        payment = get_object_or_404(

            PaymentTransaction,

            order__id=order_id,

            restaurant=restaurant,

        )

        otp = request.data.get("otp")

        if not otp:

            return Response(
                {
                    "success": False,
                    "message": "OTP is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.otp_verified:

            return Response(
                {
                    "success": False,
                    "message": "OTP already verified."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.otp_expires_at is None:

            return Response(
                {
                    "success": False,
                    "message": "OTP not generated."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > payment.otp_expires_at:

            return Response(
                {
                    "success": False,
                    "message": "OTP expired."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.completion_otp != otp:

            return Response(
                {
                    "success": False,
                    "message": "Invalid OTP."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.otp_verified = True

        payment.otp_verified_at = timezone.now()

        payment.save(
            update_fields=[
                "otp_verified",
                "otp_verified_at",
            ]
        )

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="verified",

            description="Completion OTP verified.",

            request=request,

        )

        return Response(
            {
                "success": True,
                "message": "OTP verified successfully."
            }
        )