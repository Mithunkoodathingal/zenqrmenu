"""Orders. Prices are copied onto each line when the order is placed, so later menu edits never change past orders."""
from django.db import models

from restaurants.models import Branch, Restaurant, Table


class Order(models.Model):
    class Type(models.TextChoices):
        DINEIN = "dinein"
        PICKUP = "pickup"
        DELIVERY = "delivery"

    class Status(models.TextChoices):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        PREPARING = "preparing"
        READY = "ready"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    class PaymentMethod(models.TextChoices):
        CASH = "cash"
        ONLINE = "online"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        FAILED = "failed"
        PARTIALLY_REFUNDED = "partially_refunded"
        REFUNDED = "refunded"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="orders")
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    table_number = models.CharField(max_length=20, blank=True)
    customer = models.ForeignKey("customers.CustomerProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    number = models.PositiveIntegerField()
    order_number = models.CharField(max_length=20)
    order_type = models.CharField(max_length=10, choices=Type.choices, default=Type.DINEIN)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)

    customer_name = models.CharField(max_length=150, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_note = models.TextField(blank=True)
    customer_address = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    utensils_needed = models.BooleanField(default=False)
    tip_recipient = models.CharField(max_length=12, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=20, blank=True)
    online_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    handover_code_hash = models.CharField(max_length=64, blank=True)
    handover_code_expires_at = models.DateTimeField(null=True, blank=True)
    handover_attempts = models.PositiveSmallIntegerField(default=0)
    handover_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "number"], name="unique_order_number")]
        indexes = [models.Index(fields=["restaurant", "status"]), models.Index(fields=["restaurant", "created_at"])]

    def __str__(self):
        return self.order_number

    @property
    def is_open(self):
        return self.status not in (self.Status.COMPLETED, self.Status.CANCELLED)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    food_item = models.ForeignKey("menu.FoodItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    name = models.CharField(max_length=150)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Item price plus chosen add-ons")
    quantity = models.PositiveIntegerField()
    addons = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["id"]

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class OrderEvent(models.Model):
    """Status history, shown on the diner's tracking page."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
