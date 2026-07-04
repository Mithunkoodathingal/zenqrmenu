"""
===============================================================================
Razorpay Webhook APIs

Handles:

    • payment.captured
    • payment.failed
    • Webhook verification
    • Payment synchronization
    • Audit logging

===============================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================

import hashlib
import hmac
import json

# =============================================================================
# Django Imports
# =============================================================================

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# =============================================================================
# Django REST Framework Imports
# =============================================================================

from rest_framework.response import Response
from rest_framework.views import APIView

# =============================================================================
# Local Application Imports
# =============================================================================

from payments.models import (
    PaymentTransaction,
    PaymentWebhookLog,
)

from payments.services import (
    create_audit_log,
    get_payment_settings,
)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookAPIView(APIView):

    authentication_classes = []

    permission_classes = []

    def post(self, request):

        payload = request.body.decode("utf-8")

        signature = request.headers.get(
            "X-Razorpay-Signature",
            ""
        )

        try:

            data = json.loads(payload)

        except Exception:

            return Response(
                status=400
            )

        entity = data.get("payload", {}).get("payment", {}).get("entity", {})

        gateway_order_id = entity.get("order_id")

        payment = PaymentTransaction.objects.filter(

            gateway_order_id=gateway_order_id

        ).select_related(

            "restaurant",
            "order",

        ).first()

        if payment is None:

            return Response(status=200)

        settings_obj = get_payment_settings(
            payment.restaurant
        )

        expected_signature = hmac.new(

            settings_obj.webhook_secret.encode(),

            payload.encode(),

            hashlib.sha256,

        ).hexdigest()

        verified = hmac.compare_digest(

            expected_signature,

            signature,

        )

        webhook = PaymentWebhookLog.objects.create(

            restaurant=payment.restaurant,

            event=data.get("event"),

            payload=data,

            signature=signature,

            headers=dict(request.headers),

            verified=verified,

        )

        if not verified:

            webhook.error_message = "Invalid signature"

            webhook.save(
                update_fields=[
                    "error_message"
                ]
            )

            return Response(status=400)

        event = data.get("event")

        if event == "payment.captured":

            if payment.status == "paid":
                return Response(status=200)

            payment.status = "paid"

            payment.gateway_payment_id = entity.get("id")

            payment.gateway_signature = signature

            payment.paid_at = timezone.now()

            payment.order.payment_status = "paid"

            payment.order.status = "confirmed"

            payment.order.save(
                update_fields=[
                    "payment_status",
                    "status",
                ]
            )

            payment.save(
                update_fields=[
                    "status",
                    "gateway_payment_id",
                    "gateway_signature",
                    "paid_at",
                ]
            )

        elif event == "payment.failed":

            payment.status = "failed"

            payment.failure_reason = entity.get(
                "error_description",
                ""
            )

            payment.gateway_response = entity

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "gateway_response",
                ]
            )

            payment.order.payment_status = "failed"

            payment.order.status = "payment_failed"

            payment.order.save(
                update_fields=[
                    "payment_status",
                    "status",
                ]
            )

        webhook.processed = True

        webhook.processed_at = timezone.now()

        webhook.save(
            update_fields=[
                "processed",
                "processed_at",
            ]
        )

        create_audit_log(

            restaurant=payment.restaurant,

            payment=payment,

            action="payment",

            description=f"Webhook: {event}",

        )

        return Response(
            {
                "success": True
            }
        )
    

