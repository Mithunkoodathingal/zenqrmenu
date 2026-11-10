from rest_framework.permissions import BasePermission

from .tenancy import is_customer, owned_restaurant, partner_membership, staff_membership


class NotCustomer(BasePermission):
    """Signed-in owner/staff accounts only; customer tokens can't reach restaurant tools."""

    message = "Customer accounts cannot use restaurant tools."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and not is_customer(request.user))


class IsOwnerOrRole(BasePermission):
    """Owner, or staff whose role is in view.allowed_roles.

    A signed-in owner who hasn't created a restaurant yet may still read (views return empty data).
    """

    message = "Your role can't do this."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or is_customer(user):
            return False
        if owned_restaurant(user) is not None:
            return True
        member = staff_membership(user)
        if member is not None:
            roles = getattr(view, "allowed_roles", None)
            # "owner" staff are co-owners with full access.
            return roles is None or member.role == "owner" or member.role in roles
        if partner_membership(user) is not None:
            return False
        # Owner without a restaurant yet: reads return empty data, writes answer "create your restaurant first".
        return True
