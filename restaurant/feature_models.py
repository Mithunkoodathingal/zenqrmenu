"""
Additional domain models used by the JSON API surface.

These models intentionally live outside models.py so the existing, large
restaurant model module remains untouched.  They are registered with the
restaurant Django app through RestaurantConfig.ready().
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from restaurant.models import FoodItem, Order, Restaurant


class InventoryItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="inventory_items",
        on_delete=models.CASCADE,
    )
    food_item = models.ForeignKey(
        FoodItem,
        related_name="inventory_records",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=30, default="unit")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "restaurant"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="unique_inventory_item_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "sku"]),
        ]

    def __str__(self):
        return self.name


class Coupon(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"

    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, "Percentage"),
        (DISCOUNT_FIXED, "Fixed"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        related_name="coupons",
        on_delete=models.CASCADE,
    )
    code = models.CharField(max_length=50)
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_CHOICES,
        default=DISCOUNT_PERCENT,
    )
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    applies_to_dinein = models.BooleanField(default=True)
    applies_to_pickup = models.BooleanField(default=True)
    applies_to_delivery = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "restaurant"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_coupon_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "code"]),
            models.Index(fields=["restaurant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.restaurant.name}: {self.code}"


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(
        Coupon,
        related_name="redemptions",
        on_delete=models.PROTECT,
    )
    order = models.OneToOneField(
        Order,
        related_name="coupon_redemption",
        on_delete=models.CASCADE,
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "restaurant"
        ordering = ["-created_at"]


class Review(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="reviews",
        on_delete=models.CASCADE,
    )
    order = models.ForeignKey(
        Order,
        related_name="reviews",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    owner_response = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "restaurant"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "is_published"]),
            models.Index(fields=["restaurant", "rating"]),
        ]

    def __str__(self):
        return f"{self.restaurant.name}: {self.rating}/5"
