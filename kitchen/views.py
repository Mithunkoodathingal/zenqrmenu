"""Kitchen display feed. Finished orders stay on the board for 12 hours so the Completed column survives refreshes."""
from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant
from orders.models import Order, OrderEvent
from orders.serializers import order_out
from orders.services import set_status
from orders.views import _orders

from .hooks import note_out
from .models import PRIORITIES, KitchenNote, KitchenTicket

ROLES = ["manager", "chef", "kitchen", "waiter", "cashier"]
KEEP_FINISHED = timedelta(hours=12)


def _roles(view):
    view.cls.allowed_roles = ROLES
    return view


def _who(request):
    return (request.user.get_full_name() or request.user.username or "")[:150]


@_roles
@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def kds_orders(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    since = timezone.now() - KEEP_FINISHED
    qs = _orders(request, r).filter(
        Q(status__in=["pending", "confirmed", "preparing", "ready"]) | Q(updated_at__gte=since)
    ).select_related("kitchen_ticket").prefetch_related("kitchen_notes").order_by("created_at")
    q = request.query_params
    if q.get("kitchen_status"):
        qs = qs.filter(status=q.get("kitchen_status"))
    if q.get("order_type"):
        qs = qs.filter(order_type=q.get("order_type").replace("_", ""))
    if q.get("priority"):
        p = q.get("priority")
        qs = qs.filter(kitchen_ticket__priority=p) if p != "normal" else qs.filter(Q(kitchen_ticket__isnull=True) | Q(kitchen_ticket__priority="normal"))
    return Response([order_out(o) for o in qs[:300]])


def _order(request, pk):
    return get_object_or_404(_orders(request, get_restaurant(request)), pk=pk)


@_roles
@api_view(["PATCH"])
@permission_classes([IsOwnerOrRole])
def kds_status(request, pk):
    """Mirror of the order status (the website changes the order first). Applies the same rules if called alone."""
    o = _order(request, pk)
    s = request.data.get("kitchen_status") or request.data.get("status")
    if s and s != o.status:
        o = set_status(o, s)
    return Response(order_out(_order(request, pk)))


@_roles
@api_view(["PATCH"])
@permission_classes([IsOwnerOrRole])
def kds_priority(request, pk):
    o = _order(request, pk)
    p = str(request.data.get("kitchen_priority") or request.data.get("priority") or "").lower()
    if p not in PRIORITIES:
        raise ValidationError({"kitchen_priority": ["Pick low, normal, high or urgent."]})
    KitchenTicket.objects.update_or_create(order=o, defaults={"priority": p})
    return Response(order_out(_order(request, pk)))


def _note_fields(n, d, creating):
    if "note" in d or creating:
        text = str(d.get("note") or "").strip()
        if not text:
            raise ValidationError({"note": ["Write a note."]})
        n.note = text[:2000]
    if "note_type" in d:
        n.note_type = str(d.get("note_type") or "kitchen")[:20]
    for f in ("is_internal", "is_pinned"):
        if f in d:
            setattr(n, f, str(d.get(f)).lower() in {"true", "1", "on", "yes"})


@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def kds_note(request, pk):
    o = _order(request, pk)
    n = KitchenNote(restaurant=o.restaurant, order=o, created_by=_who(request))
    _note_fields(n, request.data, True)
    n.save()
    return Response(note_out(n), status=201)


@_roles
@api_view(["GET", "POST"])
@permission_classes([IsOwnerOrRole])
def notes(request):
    r = get_restaurant(request, required=request.method == "POST")
    if request.method == "GET":
        if r is None:
            return Response([])
        qs = KitchenNote.objects.filter(restaurant=r, archived_at__isnull=True)
        q = request.query_params
        if q.get("order_id"):
            qs = qs.filter(order_id=q.get("order_id"))
        if q.get("note_type"):
            qs = qs.filter(note_type=q.get("note_type"))
        for f in ("is_internal", "is_pinned"):
            if q.get(f) not in (None, ""):
                qs = qs.filter(**{f: q.get(f).lower() in {"true", "1"}})
        return Response([note_out(n) for n in qs[:300]])
    n = KitchenNote(restaurant=r, created_by=_who(request))
    if request.data.get("order") or request.data.get("order_id"):
        n.order = _order(request, request.data.get("order") or request.data.get("order_id"))
    _note_fields(n, request.data, True)
    n.save()
    return Response(note_out(n), status=201)


@_roles
@api_view(["PATCH", "DELETE"])
@permission_classes([IsOwnerOrRole])
def note_detail(request, pk):
    n = get_object_or_404(KitchenNote, pk=pk, restaurant=get_restaurant(request), archived_at__isnull=True)
    if request.method == "DELETE":
        n.archived_at = timezone.now()  # archived, not erased
        n.save(update_fields=["archived_at"])
        return Response(status=204)
    _note_fields(n, request.data, False)
    n.save()
    return Response(note_out(n))


@_roles
@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def statistics(request):
    r = get_restaurant(request, required=False)
    empty = {"total_orders": 0, "pending": 0, "confirmed": 0, "preparing": 0, "ready": 0, "completed": 0, "cancelled": 0,
             "overdue": 0, "average_prep_minutes": None}
    if r is None:
        return Response(empty)
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today = list(_orders(request, r).filter(created_at__gte=start))
    out = dict(empty, total_orders=len(today))
    for o in today:
        out[o.status] = out.get(o.status, 0) + 1
    late = timezone.now() - timedelta(minutes=max(r.average_prep_minutes, 1) + 10)
    out["overdue"] = sum(1 for o in today if o.status in ("pending", "confirmed", "preparing") and o.created_at < late)
    durations = []
    events = OrderEvent.objects.filter(order__in=[o.id for o in today], status__in=["confirmed", "ready"]).order_by("created_at")
    first = {}
    for e in events:
        first.setdefault((e.order_id, e.status), e.created_at)
    for o in today:
        a, b = first.get((o.id, "confirmed")), first.get((o.id, "ready"))
        if a and b and b > a:
            durations.append((b - a).total_seconds() / 60)
    out["average_prep_minutes"] = round(sum(durations) / len(durations), 1) if durations else None
    return Response(out)
