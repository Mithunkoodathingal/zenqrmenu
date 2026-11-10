"""Who the caller works for. Every owner/staff endpoint scopes its data through these helpers.

Roles are separate accounts:
- owner: a User who owns a Restaurant
- staff / delivery partner: a User linked to one restaurant (added in later stages)
- customer: a User with a CustomerProfile (added in a later stage); never treated as an owner
"""
from django.apps import apps
from rest_framework.exceptions import NotFound, PermissionDenied


def owned_restaurant(user):
    if not user or not user.is_authenticated:
        return None
    from restaurants.models import Restaurant
    return Restaurant.objects.filter(owner=user, deleted_at__isnull=True).first()


def staff_membership(user):
    if not user or not user.is_authenticated or not apps.is_installed("staff"):
        return None
    member = getattr(user, "staff_member", None)
    return member if member is not None and member.is_active else None


def partner_membership(user):
    if not user or not user.is_authenticated or not apps.is_installed("delivery"):
        return None
    partner = getattr(user, "delivery_partner", None)
    return partner if partner is not None and partner.is_active else None


def is_customer(user):
    return bool(user and user.is_authenticated and hasattr(user, "customer_profile"))


def get_restaurant(request, *, required=True, allow_staff=True, allow_partner=False):
    """The restaurant the caller works for. Raises 404 when there is none and `required`."""
    user = request.user
    restaurant = owned_restaurant(user)
    if restaurant is None and allow_staff:
        member = staff_membership(user)
        restaurant = member.restaurant if member else None
    if restaurant is None and allow_partner:
        partner = partner_membership(user)
        restaurant = partner.restaurant if partner else None
    if restaurant is None and required:
        if is_customer(user):
            raise PermissionDenied("Customer accounts cannot use restaurant tools.")
        raise NotFound("No restaurant found for this account. Create your restaurant first.")
    return restaurant


def no_restaurant_yet(request):
    """A signed-in owner who hasn't created a restaurant yet (reads return empty data, not errors)."""
    user = request.user
    return (
        user.is_authenticated
        and not is_customer(user)
        and get_restaurant(request, required=False, allow_partner=True) is None
    )


def get_branch(request, restaurant):
    """Branch from ?branch= / body `branch` (validated against the restaurant); staff are pinned to theirs."""
    from restaurants.models import Branch
    member = staff_membership(request.user)
    if member and member.branch_id:
        return member.branch
    raw = request.query_params.get("branch") if hasattr(request, "query_params") else None
    if raw in (None, "", "all") and hasattr(request, "data") and isinstance(request.data, dict):
        raw = request.data.get("branch")
    if raw not in (None, "", "all"):
        try:
            return Branch.objects.get(pk=int(raw), restaurant=restaurant)
        except (Branch.DoesNotExist, TypeError, ValueError):
            raise NotFound("Branch not found.")
    return restaurant.main_branch()


def require_owner(request):
    """Only the owner (not staff) may change account-level things like branches and payment keys."""
    restaurant = get_restaurant(request, allow_staff=False)
    return restaurant
