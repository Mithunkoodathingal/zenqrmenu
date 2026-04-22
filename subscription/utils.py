# subscription/utils.py

from django.utils import timezone
from subscription.models import Subscription, SubscriptionPlan


def ensure_free_subscription(user, restaurant):
    # Get free plan
    free_plan = SubscriptionPlan.objects.filter(price=0).first()

    if not free_plan:
        raise Exception("Free plan not configured")

    # Get or create subscription
    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "restaurant": restaurant,
            "plan": free_plan,
            "start_date": timezone.now(),
            "end_date": timezone.now() + timezone.timedelta(days=3650),
            "is_active": True,
            "was_free_trial": True,
        }
    )

    # 🔥 IMPORTANT: ensure restaurant is linked
    if not subscription.restaurant:
        subscription.restaurant = restaurant
        subscription.save(update_fields=["restaurant"])

    # 🔥 DO NOT override existing plan
    # Only activate if completely inactive AND no plan
    if not subscription.plan:
        subscription.plan = free_plan
        subscription.start_date = timezone.now()
        subscription.end_date = timezone.now() + timezone.timedelta(days=3650)
        subscription.is_active = True
        subscription.was_free_trial = True
        subscription.save()

    return subscription


def check_subscription_access(restaurant):
    user = restaurant.owner

    subscription = Subscription.objects.filter(
        user=user
    ).select_related("plan").first()

    if not subscription:
        return False, "No subscription found"

    # ❌ NOT ACTIVE
    if not subscription.has_active_subscription():
        return False, "Subscription expired or inactive"

    # ❌ EXPIRED
    if not subscription.end_date or subscription.end_date < timezone.now():
        return False, "Subscription expired"

    # ❌ PLAN MISSING
    if not subscription.plan:
        return False, "No plan assigned"

    return True, subscription.plan