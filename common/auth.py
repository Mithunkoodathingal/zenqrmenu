"""Sign-in helpers shared by public endpoints that work with or without an account."""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class OptionalJWTAuthentication(JWTAuthentication):
    """Like normal sign-in, but an expired or broken token counts as signed out instead of failing.

    Used where guests are welcome (dine-in orders, public menus), so a stale saved token can't block them.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError):
            return None


def customer_of(request):
    """The signed-in diner's profile, or None (owners and staff are never diners)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "customer_profile", None)
