# restaurant/context_processors.py

def global_template_vars(request):
    """
    Returns:
      - socialaccount_providers: list of provider ids configured in allauth (e.g. ['google','facebook'])
      - has_subscription: bool (True if logged-in user's restaurant has an active subscription)
    Safe to use even if allauth is not installed.
    """
    providers = []
    try:
        # Lazy import in case allauth isn't installed in some environments
        from allauth.socialaccount import providers as allauth_providers
        providers = [p.id for p in allauth_providers.registry.get_list()]
    except Exception:
        providers = []

    has_subscription = False
    try:
        if request.user.is_authenticated:
            # your code stores Restaurant on user as .restaurant
            restaurant = getattr(request.user, "restaurant", None)
            if restaurant:
                # defensive: subscription may not exist
                try:
                    sub = getattr(restaurant, "subscription", None)
                    if sub and hasattr(sub, "has_active_subscription"):
                        has_subscription = bool(sub.has_active_subscription())
                    else:
                        # fallback: simple active flag if you used fields directly
                        has_subscription = bool(getattr(sub, "is_active", False))
                except Exception:
                    has_subscription = False
    except Exception:
        has_subscription = False

    return {
        "socialaccount_providers": providers,
        "has_subscription": has_subscription,
    }
