"""Placing orders (diners), the restaurant's order list and status changes, tracking and handover codes."""
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth import OptionalJWTAuthentication, customer_of
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant, staff_membership

from .models import Order
from .serializers import order_out, public_order_out, table_order_out
from .services import send_handover_code, set_status, verify_handover_code

ROLES = ["manager", "cashier", "waiter", "chef", "kitchen", "delivery_manager"]


def _orders(request, restaurant):
    qs = (Order.objects.filter(restaurant=restaurant, deleted_at__isnull=True)
          .select_related("restaurant", "branch").prefetch_related("items", "events"))
    member = staff_membership(request.user)
    if member and member.branch_id:
        return qs.filter(branch_id=member.branch_id)
    return qs


class OrderList(APIView):
    """GET: the restaurant's orders (newest first). POST: a diner places an order (guests: dine-in only)."""

    authentication_classes = [OptionalJWTAuthentication]
    allowed_roles = ROLES

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "POST" else [IsOwnerOrRole()]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response([])
        qs = _orders(request, r)
        q = request.query_params
        if q.get("branch") not in (None, "", "all"):
            qs = qs.filter(branch_id=q["branch"])
        if q.get("status"):
            qs = qs.filter(status__in=q["status"].split(","))
        if q.get("order_type"):
            qs = qs.filter(order_type=q["order_type"])
        start, end = parse_date(q.get("start_date") or ""), parse_date(q.get("end_date") or "")
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)
        if not (start or end or q.get("status")):
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=int(q.get("days") or 30)))
        return Response([order_out(o) for o in qs[:500]])

    def post(self, request):
        from .services import create_order
        order = create_order(request.data, customer_of(request))
        order = Order.objects.select_related("restaurant", "branch").prefetch_related("items", "events").get(pk=order.pk)
        return Response(order_out(order), status=201)


class OrderDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def _get(self, request, pk):
        return get_object_or_404(_orders(request, get_restaurant(request)), pk=pk)

    def get(self, request, pk):
        return Response(order_out(self._get(request, pk)))

    def patch(self, request, pk):
        o = self._get(request, pk)
        d = request.data
        if "status" in d:
            o = set_status(o, d.get("status"), str(d.get("note") or ""))
        if "customer_note" in d:
            o.customer_note = str(d.get("customer_note") or "")[:1000]
            o.save(update_fields=["customer_note", "updated_at"])
        return Response(order_out(self._get(request, pk)))

    put = patch

    def delete(self, request, pk):
        """Hides the order from lists. Open orders are cancelled first so stock and coupons are given back."""
        o = self._get(request, pk)
        if o.is_open:
            o = set_status(o, Order.Status.CANCELLED, "Deleted by restaurant")
        o.deleted_at = timezone.now()
        o.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=204)


@api_view(["GET"])
@authentication_classes([OptionalJWTAuthentication])
@permission_classes([AllowAny])
def public_order(request, pk):
    """Tracking page. The diner who placed it (or its restaurant) sees full detail; anyone else sees progress only."""
    o = get_object_or_404(Order.objects.select_related("restaurant", "branch").prefetch_related("items", "events"),
                          pk=pk, deleted_at__isnull=True)
    me = customer_of(request)
    if me is not None and o.customer_id == me.id:
        return Response(order_out(o))
    if request.user.is_authenticated and me is None and get_restaurant(request, required=False) == o.restaurant:
        return Response(order_out(o))
    return Response(public_order_out(o))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def table_orders(request, pk):
    """Today's orders at one table so diners there can follow them. No contact details."""
    since = timezone.now() - timedelta(hours=12)
    qs = (Order.objects.filter(table_id=pk, created_at__gte=since, deleted_at__isnull=True)
          .exclude(status=Order.Status.CANCELLED).prefetch_related("items").order_by("created_at"))
    return Response([table_order_out(o) for o in qs])


# ─── Handover code ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def generate_code(request, pk):
    o = get_object_or_404(_orders(request, get_restaurant(request)), pk=pk)
    expires = send_handover_code(o)
    return Response({"message": f"Code emailed to {o.customer_email}.", "expires_at": expires})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def verify_code(request, pk):
    o = get_object_or_404(_orders(request, get_restaurant(request)), pk=pk)
    verify_handover_code(o, request.data.get("otp") or request.data.get("code"))
    return Response({"verified": True, "message": "Code accepted."})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def complete(request, pk):
    """Hand over and complete. Pickup and delivery orders need the diner's code first."""
    o = get_object_or_404(_orders(request, get_restaurant(request)), pk=pk)
    if o.order_type != Order.Type.DINEIN and o.customer_email and not o.handover_verified_at:
        raise ValidationError({"otp": ["Enter the customer's handover code first."], "detail": "Enter the customer's handover code first."})
    set_status(o, Order.Status.COMPLETED, "Handed over")
    return Response({"success": True, "message": "Order completed."})
