"""
===============================================================================
Payment Reconciliation APIs

Handles:

    • Payment Reconciliation
    • Gateway Comparison
    • Local Comparison
    • Payment Status Synchronization
    • Order Status Synchronization

===============================================================================
"""

# =============================================================================
# Django Imports
# =============================================================================

from django.core.exceptions import ValidationError
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
    PaymentTransaction,
)

from payments.services import (
    compare_gateway_payment,
    compare_local_payment,
    create_audit_log,
    fix_order_status,
    fix_payment_status,
    get_payment_settings,
    get_restaurant_client,
)

from restaurant.utils import get_restaurant




# ==========================================================
# payments/views/reconciliation.py
# Part 7A1
# ==========================================================

from django.db import transaction

from django.shortcuts import get_object_or_404

from django.core.exceptions import ValidationError

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from restaurant.models import Order

from payments.models import (
    PaymentTransaction,
)

from .payment_settings import (
    get_restaurant,
    get_restaurant_client,
)

from payments.services import (
    compare_gateway_payment,
    compare_local_payment,
    fix_payment_status,
    fix_order_status,
)

from .audit import (
    create_audit_log,
)


# ==========================================================
# Payment Reconciliation API
# ==========================================================

class PaymentReconciliationAPIView(APIView):

    """
    Reconcile a local payment with Razorpay.

    Steps

    1. Restaurant lookup

    2. Payment lookup

    3. Fetch Razorpay payment

    4. Compare local vs gateway

    5. Fix inconsistencies

    6. Audit log

    7. Return reconciliation report
    """

    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def post(
        self,
        request,
        payment_id,
    ):

        # ==================================================
        # Restaurant
        # ==================================================

        restaurant = get_restaurant(
            request
        )

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )



        if payment.payment_method != "online":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only online payments "
                        "can be reconciled."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        # ==================================================
        # Payment
        # ==================================================

        payment = get_object_or_404(

            PaymentTransaction,

            id=payment_id,

            restaurant=restaurant,

        )

        # ==================================================
        # Order
        # ==================================================

        order = payment.order

        # ==================================================
        # Validate Gateway Payment ID
        # ==================================================

        if not payment.gateway_payment_id:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Gateway payment ID "
                        "not available."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==================================================
        # Razorpay Client
        # ==================================================

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

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to initialize "
                        "payment gateway."
                    ),
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==================================================
        # Fetch Gateway Payment
        # ==================================================

        try:

            gateway_payment = client.payment.fetch(

                payment.gateway_payment_id

            )

        except Exception as e:

            create_audit_log(

                restaurant=restaurant,

                payment=payment,

                action="failed",

                description=(
                    "Reconciliation failed. "
                    f"Gateway payment fetch error: {str(e)}"
                ),

                request=request,

            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to fetch payment "
                        "from Razorpay."
                    ),
                    "error": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


        # ==================================================
        # Fetch Gateway Order (Optional)
        # ==================================================

        gateway_order = None

        if payment.gateway_order_id:

            try:

                gateway_order = client.order.fetch(

                    payment.gateway_order_id

                )

            except Exception:

                gateway_order = None

        # ==================================================
        # Compare Gateway Payment
        # ==================================================

        gateway_comparison = compare_gateway_payment(
            payment,
            gateway_payment,
        )

        # ==================================================
        # Compare Local Payment
        # ==================================================

        local_comparison = compare_local_payment(
            payment,
        )


# ==================================================
# Continue in Part 7A2
#
# • compare_gateway_payment()
# • compare_local_payment()
# • fix_payment_status()
# • fix_order_status()
# • Audit Log
# • Response
# ==================================================

    # ==================================================
        # Fix Payment
        # ==================================================

        payment_result = fix_payment_status(
            payment=payment,
            gateway_payment=gateway_payment,
        )

        # ==================================================
        # Fix Order
        # ==================================================

        order_result = fix_order_status(
            payment=payment,
        )

        # ==================================================
        # Audit Log
        # ==================================================

        create_audit_log(

            restaurant=restaurant,

            payment=payment,

            action="reconciliation",

            description=(
                "Payment reconciliation completed. "
                f"Payment updated={payment_result['updated']}, "
                f"Order updated={order_result['updated']}."
            ),

            request=request,

        )


        # ==================================================
        # Final Response
        # ==================================================

        return Response(
            {
                "success": True,
                "message": "Payment reconciliation completed successfully.",

                "payment": {
                    "id": str(payment.id),
                    "status": payment.status,
                    "gateway_payment_id": payment.gateway_payment_id,
                    "gateway_order_id": payment.gateway_order_id,
                },

                "order": {
                    "id": str(order.id),
                    "status": order.status,
                    "payment_status": order.payment_status,
                },

                "gateway": {
                    "status": gateway_payment.get("status"),
                    "amount": gateway_payment.get("amount"),
                    "currency": gateway_payment.get("currency"),
                },

                "comparison": {
                    "gateway": gateway_comparison,
                    "local": local_comparison,
                },

                "updates": {
                    "payment": payment_result,
                    "order": order_result,
                },
            },
            status=status.HTTP_200_OK,
        )