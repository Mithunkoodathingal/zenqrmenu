"""Plan limits. A limit of 0 means unlimited."""
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import Plan, Subscription

FREE_PLAN_DEFAULTS = {"price": 0, "duration_days": 0, "table_limit": 1, "menu_item_limit": 0, "branch_limit": 0,
                      "features": "1 table QR code\nUnlimited menu items\nDine-in ordering", "position": 0}


def free_plan():
    plan = Plan.objects.filter(price=0, is_active=True).order_by("position").first()
    return plan or Plan.objects.create(name="Free", **FREE_PLAN_DEFAULTS)


def ensure_subscription(restaurant):
    """Every restaurant starts on the free plan."""
    sub = Subscription.objects.filter(restaurant=restaurant).select_related("plan").first()
    if sub is None:
        sub = Subscription.objects.create(restaurant=restaurant, plan=free_plan(), started_at=timezone.now())
    return sub


def active_plan(restaurant):
    sub = ensure_subscription(restaurant)
    if sub.plan.price > 0 and (sub.status == Subscription.Status.PAST_DUE or (sub.renews_at and sub.renews_at <= timezone.now())):
        return free_plan()
    return sub.plan


def check_limit(restaurant, kind):
    """Raise a friendly 403 when adding one more table / menu item would pass the plan limit."""
    plan = active_plan(restaurant)
    if kind == "tables":
        limit, used, label = plan.table_limit, restaurant.tables.count(), "tables"
    elif kind == "items":
        limit, used, label = plan.menu_item_limit, restaurant.items.count(), "menu items"
    else:
        limit, used, label = plan.branch_limit, restaurant.branches.count(), "branches"
    if limit and used >= limit:
        raise PermissionDenied(f"You've reached your {plan.name} plan limit of {limit} {label}. Upgrade to add more.")


def activate(restaurant, plan):
    """Switch to `plan`. Buying the plan you already have extends it from its current end date."""
    from datetime import timedelta
    sub = ensure_subscription(restaurant)
    now = timezone.now()
    if plan.price == 0:
        sub.plan, sub.status, sub.started_at, sub.renews_at = plan, Subscription.Status.ACTIVE, now, None
    else:
        base = sub.renews_at if (sub.plan_id == plan.id and sub.renews_at and sub.renews_at > now) else now
        if base == now:
            sub.started_at = now
        sub.plan, sub.status = plan, Subscription.Status.ACTIVE
        sub.renews_at = base + timedelta(days=plan.duration_days or 30)
    sub.save()
    return sub
