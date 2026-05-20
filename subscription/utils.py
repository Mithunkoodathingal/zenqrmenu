# subscription/utils.py

from datetime import timedelta

from django.utils import timezone

from subscription.models import (
    Subscription,
    SubscriptionPlan,
)


def ensure_free_subscription(user, restaurant):
    """
    Ensure restaurant always has a valid active free subscription.
    """

    free_plan = (
        SubscriptionPlan.objects.filter(price=0).first()
        or SubscriptionPlan.objects.filter(name__iexact="Free").first()
    )

    if not free_plan:
        raise Exception("Free subscription plan not configured")

    # =====================================================
    # REMOVE BROKEN SUBSCRIPTIONS
    # =====================================================

    Subscription.objects.filter(
        user=user,
        restaurant=restaurant,
        plan__isnull=True
    ).delete()

    # =====================================================
    # DEACTIVATE OLD SUBSCRIPTIONS
    # =====================================================

    Subscription.objects.filter(
        restaurant=restaurant
    ).exclude(
        plan=free_plan
    ).update(
        is_active=False
    )

    # =====================================================
    # CREATE / UPDATE FREE SUBSCRIPTION
    # =====================================================

    start_date = timezone.now()

    end_date = (
        start_date +
        timedelta(days=free_plan.duration_days)
    )

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        restaurant=restaurant,
        defaults={
            "plan": free_plan,
            "start_date": start_date,
            "end_date": end_date,
            "is_active": True,
            "was_free_trial": True,
            "is_cancelled": False,
            "cancelled_at": None,
            "auto_renew": False,
        }
    )

    # =====================================================
    # FINAL SAFETY FIXES
    # =====================================================

    if not subscription.plan:
        subscription.plan = free_plan

    if not subscription.start_date:
        subscription.start_date = start_date

    if not subscription.end_date:
        subscription.end_date = end_date

    subscription.is_active = True
    subscription.was_free_trial = True

    subscription.save()

    return subscription


def get_active_subscription(restaurant):
    """
    Get latest active subscription.
    """

    return (
        Subscription.objects
        .filter(
            restaurant=restaurant,
            is_active=True,
            plan__isnull=False
        )
        .select_related("plan")
        .order_by("-id")
        .first()
    )


def check_subscription_access(restaurant):
    """
    Check whether restaurant has valid active subscription.

    Returns:
        (True, plan)
        OR
        (False, error_message)
    """

    subscription = get_active_subscription(
        restaurant
    )

    if not subscription:
        return False, "No active subscription found"

    if not subscription.plan:
        return False, "Subscription plan missing"

    return True, subscription.plan


def can_create_table(restaurant):
    """
    Check whether restaurant can create more tables.
    """

    subscription = get_active_subscription(
        restaurant
    )

    if not subscription:
        return False

    if not subscription.plan:
        return False

    return subscription.remaining_tables() > 0


def can_add_menu_item(restaurant):
    """
    Check whether restaurant can add more menu items.
    """

    subscription = get_active_subscription(
        restaurant
    )

    if not subscription:
        return False

    if not subscription.plan:
        return False

    from restaurant.models import FoodItem

    current_items = FoodItem.objects.filter(
        restaurant=restaurant
    ).count()

    # Unlimited items
    if subscription.plan.menu_item_limit == -1:
        return True

    return (
        current_items <
        subscription.plan.menu_item_limit
    )


def activate_subscription(user, restaurant, plan):
    """
    Activate paid/free subscription safely.
    Prevent duplicate broken subscriptions.
    """

    # =====================================================
    # REMOVE BROKEN SUBSCRIPTIONS
    # =====================================================

    Subscription.objects.filter(
        user=user,
        restaurant=restaurant,
        plan__isnull=True
    ).delete()

    # =====================================================
    # DEACTIVATE OLD SUBSCRIPTIONS
    # =====================================================

    Subscription.objects.filter(
        restaurant=restaurant
    ).update(
        is_active=False
    )

    # =====================================================
    # CREATE NEW ACTIVE SUBSCRIPTION
    # =====================================================

    start_date = timezone.now()

    end_date = (
        start_date +
        timedelta(days=plan.duration_days)
    )

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        restaurant=restaurant,
        defaults={
            "plan": plan,
            "start_date": start_date,
            "end_date": end_date,
            "is_active": True,
            "was_free_trial": plan.price == 0,
            "is_cancelled": False,
            "cancelled_at": None,
            "auto_renew": plan.price > 0,
        }
    )

    return subscription


def has_active_subscription(restaurant):
    """
    IMPORTANT:
    DO NOT check end_date while debugging subscription loops.
    """

    return Subscription.objects.filter(
        restaurant=restaurant,
        is_active=True,
        plan__isnull=False
    ).exists()