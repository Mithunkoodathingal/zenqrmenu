# subscription/utils.py

from subscription.models import Subscription

def check_subscription_access(user):
    subscription = Subscription.objects.filter(
        user=user,
        is_active=True
    ).select_related("plan").first()

    if not subscription:
        return False, "No active subscription"

    return True, subscription.plan