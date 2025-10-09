# restaurant/context_processors.py
from django.conf import settings

def global_template_vars(request):
    """
    Provide:
      - socialaccount_providers (list) — optional
      - has_subscription (bool) — True if current user's restaurant has an active subscription
    Defensive: never raise an exception.
    """
    providers = []
    try:
        from allauth.socialaccount import providers as allauth_providers
        providers = [p.id for p in allauth_providers.registry.get_list()]
    except Exception:
        providers = []

    has_subscription = False
    try:
        if request.user.is_authenticated:
            restaurant = getattr(request.user, "restaurant", None)
            if restaurant:
                sub = getattr(restaurant, "subscription", None)
                # Prefer a has_active_subscription method, otherwise fall back to truthy check
                if sub:
                    if hasattr(sub, "has_active_subscription"):
                        has_subscription = bool(sub.has_active_subscription())
                    else:
                        # fallback: check fields commonly present
                        is_active = getattr(sub, "is_active", None)
                        end_date = getattr(sub, "end_date", None)
                        if is_active is not None:
                            has_subscription = bool(is_active)
                        elif end_date is not None:
                            from django.utils import timezone
                            has_subscription = (end_date and end_date > timezone.now())
                        else:
                            # last resort: truthiness
                            has_subscription = bool(sub)
                else:
                    has_subscription = False
    except Exception:
        # never propagate exceptions to templates; return False
        has_subscription = False

    return {
        "socialaccount_providers": providers,
        "has_subscription": has_subscription,
    }
