# subscription/utils.py

from django.utils import timezone
from datetime import timedelta

from subscription.models import Subscription, SubscriptionPlan
from restaurant.models import Restaurant


def ensure_free_subscription(user, restaurant):
    """
    Ensure the restaurant has a valid free subscription.
    Creates one if missing.
    """

    # Get free plan
    free_plan = (
        SubscriptionPlan.objects.filter(price=0).first()
        or SubscriptionPlan.objects.filter(name__iexact="Free").first()
    )

    if not free_plan:
        raise Exception("Free subscription plan not configured")

    # Get or create subscription
    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "restaurant": restaurant,
            "plan": free_plan,
            "start_date": timezone.now(),
            "end_date": timezone.now() + timedelta(days=free_plan.duration_days),
            "is_active": True,
            "was_free_trial": True,
        }
    )

    # Fix restaurant link if missing/wrong
    if subscription.restaurant != restaurant:
        subscription.restaurant = restaurant

    # Ensure plan exists
    if not subscription.plan:
        subscription.plan = free_plan

    # Ensure dates exist
    if not subscription.start_date:
        subscription.start_date = timezone.now()

    if not subscription.end_date:
        subscription.end_date = (
            subscription.start_date +
            timedelta(days=subscription.plan.duration_days)
        )

    # Ensure active
    if subscription.end_date >= timezone.now():
        subscription.is_active = True
    else:
        subscription.is_active = False

    # Mark free trial
    if subscription.plan.price == 0:
        subscription.was_free_trial = True

    subscription.save()

    return subscription


def check_subscription_access(restaurant):
    """
    Check whether restaurant has valid active subscription.
    Returns:
        (True, plan)
        OR
        (False, error_message)
    """

    subscription = (
        Subscription.objects
        .filter(
            restaurant=restaurant
        )
        .select_related("plan")
        .first()
    )

    if not subscription:
        return False, "No subscription found"

    if not subscription.is_active:
        return False, "Subscription inactive"

    if not subscription.end_date:
        return False, "Subscription has no expiry date"

    if subscription.end_date < timezone.now():
        subscription.is_active = False
        subscription.save(update_fields=["is_active"])
        return False, "Subscription expired"

    return True, subscription.plan


def get_active_subscription(restaurant):
    """
    Helper to get active subscription object safely.
    """

    subscription = (
        Subscription.objects
        .filter(
            restaurant=restaurant,
            is_active=True,
            end_date__gte=timezone.now()
        )
        .select_related("plan")
        .first()
    )

    return subscription


def can_create_table(restaurant):
    """
    Check if restaurant can create more tables.
    """

    subscription = get_active_subscription(restaurant)

    if not subscription:
        return False

    return subscription.remaining_tables() > 0


def can_add_menu_item(restaurant):
    """
    Check menu item limit.
    """

    subscription = get_active_subscription(restaurant)

    if not subscription:
        return False

    plan = subscription.plan

    if not plan:
        return False

    from restaurant.models import FoodItem

    current_items = FoodItem.objects.filter(
        restaurant=restaurant
    ).count()

    return current_items < plan.menu_item_limit