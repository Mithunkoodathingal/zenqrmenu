# subscription/utils.py

from datetime import timedelta
from django.utils import timezone
from subscription.models import Subscription, SubscriptionPlan
from django.shortcuts import  redirect
# from restaurant.models import Restaurant


def ensure_free_subscription(user, restaurant):
    """
    Ensure restaurant always has a valid free subscription.
    """

    free_plan = (
        SubscriptionPlan.objects.filter(price=0).first()
        or SubscriptionPlan.objects.filter(name__iexact="Free").first()
    )

    if not free_plan:
        raise Exception("Free subscription plan not configured")

    # Remove broken subscriptions
    Subscription.objects.filter(
        user=user,
        restaurant=restaurant,
        plan__isnull=True
    ).delete()

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        restaurant=restaurant,
        defaults={
            "plan": free_plan,
            "start_date": timezone.now(),
            "end_date": timezone.now() + timedelta(days=free_plan.duration_days),
            "is_active": True,
            "was_free_trial": True,
            "is_cancelled": False,
        }
    )

    # Ensure valid dates
    if not subscription.start_date:
        subscription.start_date = timezone.now()

    if not subscription.end_date:
        subscription.end_date = (
            subscription.start_date +
            timedelta(days=free_plan.duration_days)
        )

    # Ensure plan exists
    if not subscription.plan:
        subscription.plan = free_plan

    # Activate/deactivate properly
    if subscription.end_date >= timezone.now():
        subscription.is_active = True
    else:
        subscription.is_active = False

    # Free trial flag
    if subscription.plan.price == 0:
        subscription.was_free_trial = True

    subscription.save()

    return subscription


def get_active_subscription(restaurant):
    """
    Get latest active valid subscription safely.
    """

    return (
        Subscription.objects
        .filter(
            restaurant=restaurant,
            is_active=True,
            end_date__gte=timezone.now(),
            plan__isnull=False
        )
        .select_related("plan")
        .order_by("-end_date")
        .first()
    )


from django.utils import timezone
from subscription.models import Subscription


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
            restaurant=restaurant,
            is_active=True,
            plan__isnull=False,
            end_date__gte=timezone.now()
        )
        .select_related("plan")
        .order_by("-end_date")
        .first()
    )

    if not subscription:
        return False, "No active subscription found"

    if not subscription.plan:
        return False, "Subscription plan missing"

    return True, subscription.plan


def can_create_table(restaurant):
    """
    Check table limit.
    """

    subscription = get_active_subscription(restaurant)

    if not has_active_subscription(restaurant):
        return False

    if not subscription.plan:
        return False

    return subscription.remaining_tables() > 0


def can_add_menu_item(restaurant):

    subscription = get_active_subscription(restaurant)

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

    return current_items < subscription.plan.menu_item_limit


def activate_subscription(user, restaurant, plan):
    """
    Activate paid/free subscription safely.
    Prevent duplicate broken subscriptions.
    """

    # Delete broken subscriptions first
    Subscription.objects.filter(
        user=user,
        restaurant=restaurant,
        plan__isnull=True
    ).delete()

    start_date = timezone.now()
    end_date = start_date + timedelta(days=plan.duration_days)

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
        }
    )

    return subscription


def has_active_subscription(restaurant):
    return Subscription.objects.filter(
        restaurant=restaurant,
        is_active=True,
        plan__isnull=False,
        end_date__gte=timezone.now()
    ).exists()