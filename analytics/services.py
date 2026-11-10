"""Numbers for the dashboard, analytics charts and report files, all scoped to one restaurant (and the staff member's branch)."""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from orders.models import OrderEvent
from orders.views import _orders

LIVE = ["pending", "confirmed", "preparing", "ready"]


def _when(v, end=False):
    if not v:
        return None
    dt = parse_datetime(str(v))
    if dt is None:
        d = parse_date(str(v)[:10])
        if d is None:
            return None
        dt = datetime.combine(d, time.max if end else time.min)
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def window(request, restaurant, data=None):
    """Orders in the asked-for range (default: last 30 days) plus the range itself."""
    q = data if data is not None else request.query_params
    end = _when(q.get("to"), True) or timezone.now()
    start = _when(q.get("from")) or (end - timedelta(days=30))
    if start > end:
        start, end = end, start
    qs = _orders(request, restaurant).filter(created_at__gte=start, created_at__lte=end)
    if q.get("branch_id"):
        qs = qs.filter(branch_id=q.get("branch_id"))
    if q.get("order_type"):
        qs = qs.filter(order_type=str(q.get("order_type")).replace("_", ""))
    return qs, start, end


def money(v):
    return round(float(v or 0), 2)


def revenue_orders(qs):
    return [o for o in qs if o.status != "cancelled"]


def label(dt, gran):
    dt = timezone.localtime(dt)
    return {"hour": dt.strftime("%d %b %H:00"), "week": f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}",
            "month": dt.strftime("%b %Y"), "year": dt.strftime("%Y")}.get(gran, dt.strftime("%d %b"))


def series(orders, gran):
    buckets = defaultdict(Decimal)
    first = {}
    for o in orders:
        k = label(o.created_at, gran)
        buckets[k] += o.total
        first.setdefault(k, o.created_at)
    pts = sorted(buckets, key=lambda k: first[k])
    return [{"label": k, "value": money(buckets[k]), "timestamp": first[k]} for k in pts]


def split(rows, key, amount=lambda o: o.total):
    tot = defaultdict(Decimal)
    for o in rows:
        tot[key(o)] += amount(o)
    total = sum(tot.values()) or Decimal("1")
    return [{"key": k, "amount": money(v), "percent": round(float(v / total * 100), 1)} for k, v in sorted(tot.items(), key=lambda kv: -kv[1])]


def prep_minutes(order_ids):
    """confirmed → ready durations, per order."""
    first = {}
    for e in OrderEvent.objects.filter(order_id__in=order_ids, status__in=["confirmed", "ready"]).order_by("created_at"):
        first.setdefault((e.order_id, e.status), e.created_at)
    out = {}
    for oid in order_ids:
        a, b = first.get((oid, "confirmed")), first.get((oid, "ready"))
        if a and b and b > a:
            out[oid] = (b - a).total_seconds() / 60
    return out


def item_ranking(orders, limit=10, reverse=True):
    qty, rev, names = defaultdict(int), defaultdict(Decimal), {}
    for o in orders:
        for i in o.items.all():
            k = i.food_item_id or i.name
            qty[k] += i.quantity
            rev[k] += i.unit_price * i.quantity
            names[k] = i.name
    total = sum(rev.values()) or Decimal("1")
    keys = sorted(qty, key=lambda k: (qty[k], rev[k]), reverse=reverse)[:limit]
    return [{"id": k, "name": names[k], "quantity": qty[k], "revenue": money(rev[k]),
             "share_percent": round(float(rev[k] / total * 100), 1)} for k in keys]


def customer_ranking(orders, limit=10):
    agg = {}
    for o in orders:
        k = o.customer_id or o.customer_phone or o.customer_name
        if not k:
            continue
        a = agg.setdefault(k, {"id": o.customer_id or k, "name": o.customer_name or o.customer_phone, "orders": 0, "spend": Decimal("0")})
        a["orders"] += 1
        a["spend"] += o.total
    rows = sorted(agg.values(), key=lambda a: -a["spend"])[:limit]
    return [{**a, "spend": money(a["spend"])} for a in rows]

