"""
===============================================================================
Payment Settings APIs

Handles:

    • Restaurant Payment Settings
    • Razorpay Client
    • Razorpay Credential Verification
    • Audit Logging

===============================================================================
"""

# =============================================================================
# Third-Party Imports
# =============================================================================

import razorpay

# =============================================================================
# Django Imports
# =============================================================================

from django.core.exceptions import ValidationError
from django.db import transaction
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

from restaurant.models import Restaurant

from payments.services import (
    get_payment_settings,
    get_restaurant,
    get_restaurant_client,
    verify_razorpay_credentials,
    create_audit_log,
)

from payments.models import (
    PaymentAuditLog,
    RestaurantGatewaySettings,
)

from payments.serializers import (
    RestaurantGatewaySettingsSerializer,
)


def get_restaurant(request):

    try:
        return Restaurant.objects.get(owner=request.user)

    except Restaurant.DoesNotExist:
        return None
    

def get_payment_settings(restaurant):

    settings_obj, created = RestaurantGatewaySettings.objects.get_or_create(
        restaurant=restaurant
    )

    return settings_obj


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
    

class PaymentSettingsAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

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

        settings_obj = get_payment_settings(
            restaurant
        )

        serializer = RestaurantGatewaySettingsSerializer(
            settings_obj
        )

        return Response(
            serializer.data
        )
    
    @transaction.atomic
    def post(self, request):

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        settings_obj = get_payment_settings(
            restaurant
        )

        serializer = RestaurantGatewaySettingsSerializer(

            settings_obj,

            data=request.data,

            partial=True,

        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        create_audit_log(

            restaurant=restaurant,

            action="updated",

            description="Updated payment settings.",

            request=request,

        )

        return Response(
            serializer.data
        )
    
    @transaction.atomic
    def put(self, request):

        return self.post(request)
    

class VerifyRazorpayAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request):

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        settings_obj = get_payment_settings(
            restaurant
        )

        success, error = verify_razorpay_credentials(
            settings_obj
        )

        create_audit_log(

            restaurant=restaurant,

            action="verified",

            description=(
                "Razorpay credentials verified."
                if success
                else error
            ),

            request=request,

        )

        if success:

            return Response({

                "success": True,

                "verified": True,

                "message": "Credentials verified successfully."

            })

        return Response({

            "success": False,

            "verified": False,

            "message": error,

        }, status=400)
    
