def check_subscription_access(restaurant):
    try:
        sub = restaurant.subscription

        if not sub.is_active:
            return False, "Subscription inactive"

        return True, sub.plan
    except:
        return False, "No subscription"