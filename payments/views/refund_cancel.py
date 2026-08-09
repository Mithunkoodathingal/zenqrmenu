from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import PaymentRefund
from restaurant.services.common import get_restaurant


class RefundCancelAPIView(APIView):
    """Cancel a refund only while it is still pending/processing.

    A Razorpay refund already returned as processed cannot be reversed by
    this API. In that case the frontend receives a clear 400 response.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, refund_id):
        restaurant = get_restaurant(request)
        if restaurant is None:
            return Response({"success": False, "message": "Restaurant not found."}, status=404)

        refund = get_object_or_404(
            PaymentRefund,
            id=refund_id,
            payment__restaurant=restaurant,
        )

        if refund.status in ("processed", "failed", "cancelled"):
            return Response(
                {
                    "success": False,
                    "message": f"Refund cannot be cancelled because its current status is '{refund.status}'.",
                },
                status=400,
            )

        refund.status = "cancelled"
        refund.save(update_fields=["status"])

        return Response(
            {
                "success": True,
                "message": "Refund cancelled successfully.",
                "refund": {
                    "id": str(refund.id),
                    "refund_id": refund.refund_id,
                    "status": refund.status,
                    "cancelled_at": timezone.now(),
                },
            }
        )
