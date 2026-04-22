# subscription/utils.py

from django.utils import timezone
from subscription.models import Subscription, SubscriptionPlan


def ensure_free_subscription(user, restaurant):
    free_plan = SubscriptionPlan.objects.filter(price=0).first()

    if not free_plan:
        raise Exception("Free plan not configured")

    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "restaurant": restaurant,
            "plan": free_plan,
        }
    )

    # 🔥 ensure it's active
    if not subscription.is_active:
        subscription.plan = free_plan
        subscription.start_date = timezone.now()
        subscription.end_date = timezone.now() + timezone.timedelta(days=3650)
        subscription.is_active = True
        subscription.save()

    return subscription

def check_subscription_access(user):
    subscription = Subscription.objects.filter(
        user=user
    ).select_related("plan").first()

    if not subscription:
        return False, "No subscription found"

    if not subscription.is_active:
        return False, "Subscription inactive"

    if not subscription.end_date or subscription.end_date < timezone.now():
        return False, "Subscription expired"

    return True, subscription.plan