"""
Additional domain models used by the JSON API surface.

These models intentionally live outside models.py so the existing, large
restaurant model module remains untouched.  They are registered with the
restaurant Django app through RestaurantConfig.ready().
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

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


# =============================================================================
# BRANCH
# =============================================================================

class Branch(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="branches",
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=150)

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    state = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return self.name


# =============================================================================
# INVENTORY TRANSACTION
# =============================================================================

class InventoryTransaction(models.Model):
    REASON_CHOICES = [
        ("restock", "Restock"),
        ("waste", "Waste"),
        ("correction", "Correction"),
        ("consumed", "Consumed"),
        ("other", "Other"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        related_name="inventory_transactions",
        on_delete=models.CASCADE,
    )

    ingredient = models.ForeignKey(
        InventoryItem,
        related_name="transactions",
        on_delete=models.CASCADE,
    )

    delta = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default="correction",
    )

    note = models.TextField(
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]


# =============================================================================
# INVENTORY PURCHASE
# =============================================================================

class InventoryPurchase(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="inventory_purchases",
        on_delete=models.CASCADE,
    )

    ingredient = models.ForeignKey(
        InventoryItem,
        related_name="purchases",
        on_delete=models.CASCADE,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    supplier = models.CharField(
        max_length=150,
        blank=True,
    )

    invoice_no = models.CharField(
        max_length=100,
        blank=True,
    )

    purchased_at = models.DateTimeField(
        default=timezone.now,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    class Meta:
        ordering = ["-purchased_at"]


# =============================================================================
# APP NOTIFICATION
# =============================================================================

class AppNotification(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="notifications",
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="zenqr_notifications",
        on_delete=models.CASCADE,
    )

    notification_type = models.CharField(
        max_length=60,
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    order = models.ForeignKey(
        Order,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="app_notifications",
    )

    read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]


# =============================================================================
# NOTIFICATION PREFERENCES
# =============================================================================

class NotificationPreference(models.Model):
    restaurant = models.OneToOneField(
        Restaurant,
        related_name="notification_preferences",
        on_delete=models.CASCADE,
    )

    browser_enabled = models.BooleanField(
        default=True,
    )

    email_enabled = models.BooleanField(
        default=True,
    )

    email_address = models.EmailField(
        blank=True,
    )

    whatsapp_enabled = models.BooleanField(
        default=False,
    )

    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
    )

    push_enabled = models.BooleanField(
        default=False,
    )

    events = models.JSONField(
        default=dict,
        blank=True,
    )


# =============================================================================
# SCHEDULED REPORT
# =============================================================================

class ScheduledReport(models.Model):
    REPORT_TYPES = [
        ("payments", "Payments"),
        ("refunds", "Refunds"),
        ("orders", "Orders"),
        ("sales", "Sales"),
        ("tax", "Tax"),
        ("customers", "Customers"),
        ("delivery", "Delivery"),
        ("staff", "Staff"),
        ("coupons", "Coupons"),
        ("menu", "Menu"),
    ]

    FORMATS = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("pdf", "PDF"),
    ]

    FREQUENCIES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    DESTINATIONS = [
        ("email", "Email"),
        ("download", "Download"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        related_name="scheduled_reports",
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPES,
    )

    format = models.CharField(
        max_length=10,
        choices=FORMATS,
    )

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCIES,
    )

    destination = models.CharField(
        max_length=20,
        choices=DESTINATIONS,
    )

    email = models.EmailField(
        blank=True,
    )

    enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    next_run_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]