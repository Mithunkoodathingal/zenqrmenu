"""Plans, the owner's current plan, paid upgrades through the platform's Razorpay account, cancellation and invoices."""
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.tenancy import get_restaurant, require_owner

from .models import Plan, Subscription, SubscriptionInvoice
from .services import activate, active_plan, ensure_subscription


def plan_out(p):
    return {"id": p.id, "name": p.name, "price": float(p.price), "duration_days": p.duration_days,
            "table_limit": p.table_limit, "menu_item_limit": p.menu_item_limit, "branch_limit": p.branch_limit,
            "features": [f.strip() for f in p.features.splitlines() if f.strip()], "popular": p.popular}


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def plans(request):
    return Response([plan_out(p) for p in Plan.objects.filter(is_active=True)])


@api_view(["GET"])
def status_view(request):
    """Used by the dashboard to gate tables/menu items."""
    restaurant = get_restaurant(request, required=False)
    if restaurant is None:
        return Response({"has_subscription": False, "is_active": False, "plan": "", "table_limit": 0, "menu_item_limit": 0})
    sub = ensure_subscription(restaurant)
    plan = active_plan(restaurant)
    return Response({
        "has_subscription": True, "is_active": True, "plan": plan.name.lower(), "plan_id": plan.id,
        "price": float(plan.price), "table_limit": plan.table_limit or 100000,
        "menu_item_limit": plan.menu_item_limit, "branch_limit": plan.branch_limit,
        "status": sub.status, "renews_at": sub.renews_at,
    })


@api_view(["GET"])
def current(request):
    restaurant = get_restaurant(request, required=False)
    if restaurant is None:
        return Response({"plan": "", "status": "cancelled", "started_at": None, "renews_at": None, "days_remaining": 0})
    sub = ensure_subscription(restaurant)
    plan = active_plan(restaurant)
    days = max(0, (sub.renews_at - timezone.now()).days) if sub.renews_at else None
    state = sub.status if plan.id == sub.plan_id else "past_due"
    return Response({"plan": plan.name, "plan_id": plan.id, "status": state, "started_at": sub.started_at,
                     "renews_at": sub.renews_at, "days_remaining": days})


@api_view(["GET"])
def usage(request):
    restaurant = get_restaurant(request, required=False)
    if restaurant is None:
        zero = {"used": 0, "limit": 0}
        return Response({"qr_codes": zero, "tables": zero, "storage": {"used_mb": 0, "limit_mb": 0}, "menu_items": zero})
    plan = active_plan(restaurant)
    tables = restaurant.tables.count()
    # A limit of 0 on a plan means unlimited; the website shows null as "Unlimited".
    cap = lambda n: n or None  # noqa: E731
    return Response({
        "qr_codes": {"used": tables + 2, "limit": (plan.table_limit + 2) if plan.table_limit else None},
        "tables": {"used": tables, "limit": cap(plan.table_limit)},
        "storage": {"used_mb": round(_storage_bytes(restaurant) / 1048576, 2), "limit_mb": cap(plan.storage_limit_mb)},
        "menu_items": {"used": restaurant.items.count(), "limit": cap(plan.menu_item_limit)},
    })


def _storage_bytes(restaurant):
    total = 0
    files = [restaurant.logo, restaurant.cover_image] + [i.image for i in restaurant.items.exclude(image="").exclude(image=None)]
    for f in files:
        try:
            if f:
                total += f.size
        except (OSError, ValueError):
            pass
    return total


def _plan_from(d):
    raw = d.get("plan_id", d.get("plan"))
    if raw in (None, ""):
        raise ValidationError({"plan_id": ["Pick a plan."]})
    qs = Plan.objects.filter(is_active=True)
    plan = qs.filter(pk=raw).first() if str(raw).isdigit() else qs.filter(name__iexact=str(raw)).first()
    if plan is None:
        raise ValidationError({"plan_id": ["That plan isn't available."]})
    return plan


@api_view(["POST"])
def create(request):
    """Start buying a plan. Free plans switch at once; paid plans return a Razorpay order to pay."""
    from payments import gateway
    restaurant = require_owner(request)
    plan = _plan_from(request.data)
    if plan.price == 0:
        activate(restaurant, plan)
        return Response({"free": True, "success": True, "message": f"You're now on the {plan.name} plan."})
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return Response({"detail": "Plan payments aren't set up on the server yet."}, status=503)
    amount = int(plan.price * 100)
    try:
        rz = gateway.create_order(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET, amount, f"plan-{restaurant.id}-{plan.id}",
                                  {"restaurant_id": str(restaurant.id), "plan_id": str(plan.id)})
    except gateway.GatewayError as e:
        return Response({"detail": str(e)}, status=502)
    SubscriptionInvoice.objects.create(restaurant=restaurant, plan=plan, amount=plan.price, razorpay_order_id=rz["id"])
    return Response({"order_id": rz["id"], "razorpay_order_id": rz["id"], "amount": amount, "currency": "INR",
                     "key": settings.RAZORPAY_KEY_ID, "razorpay_key": settings.RAZORPAY_KEY_ID, "plan": plan.name})


upgrade = create


@api_view(["POST"])
def verify(request):
    from payments import gateway
    restaurant = require_owner(request)
    d = request.data
    inv = get_object_or_404(SubscriptionInvoice, restaurant=restaurant, razorpay_order_id=str(d.get("razorpay_order_id") or ""))
    if inv.status == SubscriptionInvoice.Status.PAID:
        return Response({"success": True, "message": "Already active."})
    if not gateway.signature_ok(settings.RAZORPAY_KEY_SECRET, inv.razorpay_order_id, str(d.get("razorpay_payment_id") or ""),
                                d.get("razorpay_signature")):
        inv.status = SubscriptionInvoice.Status.FAILED
        inv.save(update_fields=["status"])
        return Response({"success": False, "detail": "We couldn't confirm this payment."}, status=400)
    with transaction.atomic():
        inv.status, inv.paid_at, inv.razorpay_payment_id = SubscriptionInvoice.Status.PAID, timezone.now(), str(d["razorpay_payment_id"])
        n = SubscriptionInvoice.objects.filter(status=SubscriptionInvoice.Status.PAID, paid_at__year=inv.paid_at.year).count() + 1
        inv.number = f"ZQ-{inv.paid_at.year}-{n:05d}"
        inv.save()
        activate(restaurant, inv.plan)
    return Response({"success": True, "message": f"You're now on the {inv.plan.name} plan."})


@api_view(["POST"])
def cancel(request):
    """Stop renewing. The paid plan keeps working until its end date, then the account moves to Free."""
    restaurant = require_owner(request)
    sub = ensure_subscription(restaurant)
    if sub.plan.price == 0:
        raise ValidationError({"detail": "You're on the free plan; there's nothing to cancel."})
    sub.status = Subscription.Status.CANCELLED
    sub.save(update_fields=["status", "updated_at"])
    return Response({"success": True, "message": "Cancelled. Your plan stays active until it ends.", "renews_at": sub.renews_at})


@api_view(["GET"])
def invoices(request):
    restaurant = get_restaurant(request, required=False)
    if restaurant is None:
        return Response([])
    rows = SubscriptionInvoice.objects.filter(restaurant=restaurant).exclude(status=SubscriptionInvoice.Status.PENDING)
    return Response([{"id": i.id, "number": i.number or f"Unpaid {i.id}", "plan": i.plan.name, "amount": float(i.amount),
                      "currency": i.currency, "status": i.status, "issued_at": i.paid_at or i.issued_at, "pdf_url": None}
                     for i in rows])
