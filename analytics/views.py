"""Dashboard tiles, analytics charts, report downloads and scheduled reports."""
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant
from orders.views import _orders

from . import reports
from .models import FORMATS, FREQUENCIES, REPORT_TYPES, ScheduledReport
from .services import (LIVE, customer_ranking, item_ranking, money, prep_minutes, revenue_orders, series, split, window)

ROLES = ["manager"]


def _roles(view):
    view.cls.allowed_roles = ROLES
    return view


def endpoint(fn):
    """GET view: the restaurant's orders in range → numbers. No restaurant yet → empty result."""
    @_roles
    @api_view(["GET"])
    @permission_classes([IsOwnerOrRole])
    def view(request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response({})
        qs, start, end = window(request, r)
        return Response(fn(request, r, list(qs.prefetch_related("items")), start, end))
    view.__name__ = fn.__name__
    return view


@_roles
@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def widgets(request):
    r = get_restaurant(request, required=False)
    out = {"todays_orders": 0, "live_orders": 0, "kitchen_load": 0, "delivery_load": 0, "pending_payments": 0, "todays_revenue": 0}
    if r is None:
        return Response(out)
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    base = _orders(request, r)
    today = list(base.filter(created_at__gte=start))
    live = base.filter(status__in=LIVE)
    prep = prep_minutes([o.id for o in today])
    out.update({"todays_orders": len(today), "todays_revenue": money(sum(o.total for o in revenue_orders(today))),
                "live_orders": live.count(), "kitchen_load": live.filter(status__in=["confirmed", "preparing"]).count(),
                "delivery_load": live.filter(order_type="delivery").count(),
                "pending_payments": base.filter(payment_status="pending").exclude(status="cancelled").count(),
                "avg_prep_minutes": round(sum(prep.values()) / len(prep), 1) if prep else None})
    from reviews.services import public_reviews, summary
    avg, n = summary(public_reviews(r))
    out["customer_satisfaction"] = avg if n else None
    return Response(out)


def _kpis(orders):
    paid = revenue_orders(orders)
    rev = sum((o.total for o in paid), Decimal("0"))
    return {"revenue": rev, "orders": len(orders), "aov": rev / len(paid) if paid else Decimal("0"),
            "cancelled": sum(1 for o in orders if o.status == "cancelled")}


@endpoint
def executive(request, r, orders, start, end):
    prev_qs = _orders(request, r).filter(created_at__gte=start - (end - start), created_at__lt=start)
    now, before = _kpis(orders), _kpis(list(prev_qs))

    def kpi(key, lbl, fmt):
        v, p = float(now[key]), float(before[key])
        return {"key": key, "label": lbl, "value": round(v, 2), "previous": round(p, 2), "format": fmt,
                "delta_percent": round((v - p) / p * 100, 1) if p else None}
    return {"currency": "INR", "generated_at": timezone.now(),
            "kpis": [kpi("revenue", "Revenue", "currency"), kpi("orders", "Orders", "number"),
                     kpi("aov", "Average order", "currency"), kpi("cancelled", "Cancelled", "number")]}


@endpoint
def summary(request, r, orders, start, end):
    k = _kpis(orders)
    return {"revenue": money(k["revenue"]), "orders": k["orders"], "average_order_value": money(k["aov"]),
            "cancelled": k["cancelled"], "customers": len({o.customer_id or o.customer_phone for o in orders if o.customer_id or o.customer_phone}),
            "from": start, "to": end}


def _sales(gran_default):
    def fn(request, r, orders, start, end):
        gran = request.query_params.get("granularity") or gran_default
        paid = revenue_orders(orders)
        return {"granularity": gran, "points": series(paid, gran), "total": money(sum(o.total for o in paid)), "currency": "INR"}
    return fn


sales = endpoint(_sales("day"))
daily_sales = endpoint(_sales("day"))
monthly_sales = endpoint(_sales("month"))


@endpoint
def heatmap(request, r, orders, start, end):
    cells = defaultdict(int)
    for o in revenue_orders(orders):
        t = timezone.localtime(o.created_at)
        cells[(t.weekday(), t.hour)] += 1
    return [{"weekday": d, "hour": h, "value": cells[(d, h)]} for d in range(7) for h in range(24)]


@endpoint
def revenue(request, r, orders, start, end):
    paid = revenue_orders(orders)
    gross = sum((o.subtotal + o.tax_amount + o.delivery_charge + o.tip_amount for o in paid), Decimal("0"))
    disc = sum((o.discount_amount + o.online_discount for o in paid), Decimal("0"))
    return {"by_order_type": split(paid, lambda o: o.order_type), "by_payment_method": split(paid, lambda o: o.payment_method),
            "gateway_split": split(paid, lambda o: "razorpay" if o.payment_method == "online" else "cash"),
            "tax_collected": money(sum(o.tax_amount for o in paid)), "tips_collected": money(sum(o.tip_amount for o in paid)),
            "packing_charges": 0, "delivery_charges": money(sum(o.delivery_charge for o in paid)),
            "discounts": money(disc), "gross_revenue": money(gross), "net_revenue": money(gross - disc), "currency": "INR"}


@endpoint
def payment_methods(request, r, orders, start, end):
    paid = revenue_orders(orders)
    counts = defaultdict(int)
    for o in paid:
        counts[o.payment_method] += 1
    return [{**row, "count": counts[row["key"]]} for row in split(paid, lambda o: o.payment_method)]


@endpoint
def refunds(request, r, orders, start, end):
    from payments.models import Refund
    rows = list(Refund.objects.filter(payment__order_id__in=[o.id for o in orders]).select_related("payment"))
    done = [f for f in rows if f.status == "processed"]
    by_reason, by_gateway = defaultdict(lambda: [Decimal("0"), 0]), defaultdict(lambda: [Decimal("0"), 0])
    for f in done:
        for bucket, k in ((by_reason, f.reason or "Not given"), (by_gateway, f.payment.gateway)):
            bucket[k][0] += f.amount
            bucket[k][1] += 1
    full = sum(1 for f in done if f.amount >= f.payment.amount)
    return {"total_refunded": money(sum(f.amount for f in done)), "full_refunds": full, "partial_refunds": len(done) - full,
            "failed_refunds": sum(1 for f in rows if f.status == "failed"),
            "by_reason": [{"key": k, "amount": money(v[0]), "count": v[1]} for k, v in by_reason.items()],
            "by_gateway": [{"key": k, "amount": money(v[0]), "count": v[1]} for k, v in by_gateway.items()],
            "by_time": [{"label": p["label"], "value": p["value"]} for p in
                        _refund_series(done)], "currency": "INR"}


def _refund_series(done):
    tot = defaultdict(Decimal)
    for f in sorted(done, key=lambda f: f.created_at):
        tot[timezone.localtime(f.created_at).strftime("%d %b")] += f.amount
    return [{"label": k, "value": money(v)} for k, v in tot.items()]


def _category_ranking(orders):
    from menu.models import FoodItem
    cats = dict(FoodItem.objects.filter(pk__in={i.food_item_id for o in orders for i in o.items.all() if i.food_item_id})
                .values_list("id", "category__name"))
    qty, rev = defaultdict(int), defaultdict(Decimal)
    for o in orders:
        for i in o.items.all():
            k = cats.get(i.food_item_id) or "Other"
            qty[k] += i.quantity
            rev[k] += i.unit_price * i.quantity
    total = sum(rev.values()) or Decimal("1")
    return [{"id": k, "name": k, "quantity": qty[k], "revenue": money(rev[k]), "share_percent": round(float(rev[k] / total * 100), 1)}
            for k in sorted(rev, key=lambda k: -rev[k])[:10]]


def _addon_ranking(orders):
    qty, rev = defaultdict(int), defaultdict(Decimal)
    for o in orders:
        for i in o.items.all():
            for a in i.addons or []:
                name = a.get("name") if isinstance(a, dict) else str(a)
                qty[name] += i.quantity
                rev[name] += Decimal(str((a.get("price") if isinstance(a, dict) else 0) or 0)) * i.quantity
    total = sum(rev.values()) or Decimal("1")
    return [{"id": k, "name": k, "quantity": qty[k], "revenue": money(rev[k]), "share_percent": round(float(rev[k] / total * 100), 1)}
            for k in sorted(qty, key=lambda k: -qty[k])[:10]]


@endpoint
def menu(request, r, orders, start, end):
    paid = revenue_orders(orders)
    return {"top_categories": _category_ranking(paid), "top_items": item_ranking(paid), "top_addons": _addon_ranking(paid),
            "bottom_items": item_ranking(paid, reverse=False), "currency": "INR"}


@endpoint
def top_items(request, r, orders, start, end):
    return item_ranking(revenue_orders(orders))


@endpoint
def top_customers(request, r, orders, start, end):
    return customer_ranking(revenue_orders(orders))


@endpoint
def customers(request, r, orders, start, end):
    paid = revenue_orders(orders)
    keys = {o.customer_id or o.customer_phone for o in paid if o.customer_id or o.customer_phone}
    earlier_ids = set(_orders(request, r).filter(created_at__lt=start, customer_id__isnull=False).values_list("customer_id", flat=True))
    earlier_phones = set(_orders(request, r).filter(created_at__lt=start).exclude(customer_phone="").values_list("customer_phone", flat=True))
    returning = {k for k in keys if k in earlier_ids or k in earlier_phones}
    counts = defaultdict(int)
    for o in paid:
        if o.customer_id or o.customer_phone:
            counts[o.customer_id or o.customer_phone] += 1
    spend = sum(o.total for o in paid if o.customer_id or o.customer_phone)
    return {"new_customers": len(keys - returning), "returning_customers": len(returning),
            "repeat_purchase_percent": round(sum(1 for v in counts.values() if v > 1) / len(counts) * 100, 1) if counts else 0,
            "average_spend": money(spend / len(keys)) if keys else 0, "top_customers": customer_ranking(paid),
            "favorite_categories": _category_ranking(paid), "currency": "INR"}


@endpoint
def delivery(request, r, orders, start, end):
    from delivery.models import DeliveryAssignment
    deliveries = [o for o in orders if o.order_type == "delivery"]
    trips = list(DeliveryAssignment.objects.filter(order__in=[o.id for o in deliveries]).select_related("partner", "order"))
    done = [t for t in trips if t.status == "delivered"]

    def minutes(t):
        return (t.delivered_at - t.order.created_at).total_seconds() / 60 if t.delivered_at else None
    times = [m for m in map(minutes, done) if m is not None]
    target = (r.average_prep_minutes or 20) + 30
    per = defaultdict(list)
    for t in done:
        per[t.partner].append(minutes(t))
    dist = [float(o.delivery_distance_km) for o in deliveries if o.delivery_distance_km is not None]
    finished = [o for o in deliveries if o.status in ("completed", "cancelled")]
    return {"average_delivery_time_minutes": round(sum(times) / len(times), 1) if times else 0,
            "average_distance_km": round(sum(dist) / len(dist), 2) if dist else 0,
            "success_rate_percent": round(sum(1 for o in finished if o.status == "completed") / len(finished) * 100, 1) if finished else 0,
            "late_delivery_percent": round(sum(1 for m in times if m > target) / len(times) * 100, 1) if times else 0,
            "delivery_revenue": money(sum(o.delivery_charge for o in deliveries if o.status != "cancelled")),
            "partner_performance": [{"id": p.id, "name": p.full_name, "deliveries": len(ms),
                                     "average_time_minutes": round(sum(ms) / len(ms), 1),
                                     "on_time_percent": round(sum(1 for m in ms if m <= target) / len(ms) * 100, 1)}
                                    for p, ms in per.items()]}


@endpoint
def kitchen(request, r, orders, start, end):
    prep = prep_minutes([o.id for o in orders])
    ranked = sorted(prep.items(), key=lambda kv: kv[1])
    queue = _orders(request, r).filter(status__in=["confirmed", "preparing"]).count()
    return {"average_prep_time_minutes": round(sum(prep.values()) / len(prep), 1) if prep else 0, "queue_length": queue,
            "utilization_percent": min(100, queue * 10),
            "fastest_orders": [{"order_id": k, "minutes": round(v, 1)} for k, v in ranked[:5]],
            "slowest_orders": [{"order_id": k, "minutes": round(v, 1)} for k, v in ranked[::-1][:5]]}


@endpoint
def coupons(request, r, orders, start, end):
    from coupons.models import CouponRedemption
    reds = list(CouponRedemption.objects.filter(order__in=[o.id for o in orders]).select_related("coupon", "order"))
    per = defaultdict(lambda: [0, Decimal("0"), Decimal("0")])
    for x in reds:
        per[x.coupon.code][0] += 1
        per[x.coupon.code][1] += x.order.total
        per[x.coupon.code][2] += x.discount
    paid = revenue_orders(orders)
    return {"total_redemptions": len(reds), "redemption_rate_percent": round(len(reds) / len(paid) * 100, 1) if paid else 0,
            "revenue_generated": money(sum(x.order.total for x in reds)), "discount_given": money(sum(x.discount for x in reds)),
            "top_coupons": [{"code": k, "redemptions": v[0], "revenue": money(v[1]), "discount": money(v[2])}
                            for k, v in sorted(per.items(), key=lambda kv: -kv[1][0])]}


@endpoint
def staff(request, r, orders, start, end):
    from staff.models import Attendance, StaffMember
    hours = defaultdict(float)
    for a in Attendance.objects.filter(staff__restaurant=r, clock_in__gte=start, clock_in__lte=end):
        hours[a.staff_id] += ((a.clock_out or timezone.now()) - a.clock_in).total_seconds() / 3600
    days = max((end - start).days, 1)
    kitchen_load = sum(1 for o in orders if o.status != "cancelled")
    delivery_load = sum(1 for o in orders if o.order_type == "delivery" and o.status != "cancelled")
    return {"members": [{"id": s.id, "name": f"{s.first_name} {s.last_name}".strip(), "role": s.role,
                         "orders_handled": 0, "kitchen_workload": kitchen_load if s.role in ("chef", "kitchen") else 0,
                         "delivery_workload": delivery_load if s.role == "delivery_manager" else 0,
                         "shift_utilization_percent": round(min(100, hours[s.id] / (days * 8) * 100), 1),
                         "last_login": s.user.last_login if s.user_id else None}
                        for s in StaffMember.objects.filter(restaurant=r).select_related("user")]}


# ─── Reports ──────────────────────────────────────────────────────────────

@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def export(request):
    r = get_restaurant(request)
    kind, fmt = request.data.get("type"), request.data.get("format") or "csv"
    if kind not in REPORT_TYPES:
        raise ValidationError({"type": ["Pick a report."]})
    if fmt not in FORMATS:
        raise ValidationError({"format": ["Pick CSV, Excel or PDF."]})
    content, mime = reports.build(request, r, kind, fmt, request.data)
    resp = HttpResponse(content, content_type=mime)
    resp["Content-Disposition"] = f'attachment; filename="{kind}-{timezone.localdate().isoformat()}.{fmt}"'
    return resp


def scheduled_out(s):
    return {"id": s.id, "type": s.type, "format": s.format, "frequency": s.frequency, "destination": s.destination,
            "email": s.email, "enabled": s.enabled, "created_at": s.created_at, "next_run_at": s.next_run_at}


def _apply_schedule(s, d, creating):
    errors = {}
    for f, allowed in (("type", REPORT_TYPES), ("format", FORMATS), ("frequency", list(FREQUENCIES)), ("destination", ["email", "download"])):
        if f in d or creating:
            v = d.get(f, getattr(s, f))
            if v not in allowed:
                errors[f] = [f"Pick one of: {', '.join(allowed)}."]
            else:
                setattr(s, f, v)
    if "email" in d:
        s.email = str(d.get("email") or "").strip().lower()
    if s.destination == "email":
        s.email = s.email or s.restaurant.email
        try:
            validate_email(s.email)
        except DjangoValidationError:
            errors["email"] = ["Enter the email to send it to."]
    if "enabled" in d:
        s.enabled = bool(d.get("enabled"))
    if errors:
        raise ValidationError(errors)
    if s.enabled and (creating or s.next_run_at is None or "frequency" in d):
        s.schedule_next()
    s.save()
    return s


@_roles
@api_view(["GET", "POST"])
@permission_classes([IsOwnerOrRole])
def scheduled(request):
    r = get_restaurant(request, required=request.method == "POST")
    if request.method == "GET":
        return Response([scheduled_out(s) for s in ScheduledReport.objects.filter(restaurant=r)] if r else [])
    return Response(scheduled_out(_apply_schedule(ScheduledReport(restaurant=r), request.data, True)), status=201)


@_roles
@api_view(["PATCH", "DELETE"])
@permission_classes([IsOwnerOrRole])
def scheduled_detail(request, pk):
    s = get_object_or_404(ScheduledReport, pk=pk, restaurant=get_restaurant(request))
    if request.method == "DELETE":
        s.delete()
        return Response(status=204)
    return Response(scheduled_out(_apply_schedule(s, request.data, False)))

