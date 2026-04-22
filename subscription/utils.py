
from subscription.models import Subscription

def check_subscription_access(restaurant):
    subscription = Subscription.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).first()

    if not subscription:
        return False, "No active subscription"

    return True, subscription.plan