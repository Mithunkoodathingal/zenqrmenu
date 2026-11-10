"""The shared menu as seen at one branch: overrides, hidden categories and (later) stock decide what diners can order."""
from decimal import Decimal

from django.apps import apps

from common.geo import money

from .models import BranchCategoryOverride, BranchItemOverride


def normalize_pricing(price, original_price):
    """`price` is charged. Keep `original_price` only when it is higher, so the discount is real."""
    price = money(price)
    if original_price in (None, ""):
        return price, None
    original = money(original_price)
    return price, (original if original > price > 0 else None)


def discount_percent(price, original):
    if not original or original <= 0 or price >= original:
        return 0
    return int(round((1 - Decimal(price) / Decimal(original)) * 100))


class BranchMenu:
    """Loads overrides for one branch once, then answers per item."""

    def __init__(self, restaurant, branch):
        self.restaurant, self.branch = restaurant, branch
        self.items = {o.food_item_id: o for o in BranchItemOverride.objects.filter(branch=branch)}
        self.hidden_categories = set(BranchCategoryOverride.objects.filter(branch=branch, is_available=False).values_list("category_id", flat=True))
        self.portions = None
        if apps.is_installed("inventory"):
            from inventory.services import portions_map
            self.portions = portions_map(restaurant, branch)

    def price(self, item):
        o = self.items.get(item.id)
        return money(o.price) if o and o.price is not None else money(item.price)

    def portions_left(self, item):
        if self.portions is None:
            return None
        return self.portions.get(item.id)

    def unavailable_reason(self, item):
        o = self.items.get(item.id)
        if not item.is_available:
            return "Paused by restaurant"
        if o and o.is_available is False:
            return "Not served at this branch"
        if item.category_id in self.hidden_categories:
            return "Category hidden at this branch"
        left = self.portions_left(item)
        if left is not None and left < 1:
            return "Out of stock"
        return None
