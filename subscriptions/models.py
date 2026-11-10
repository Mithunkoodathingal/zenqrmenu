from django.db import models

from restaurants.models import Restaurant


class Plan(models.Model):
    """Limits: 0 means unlimited."""

    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)
    table_limit = models.PositiveIntegerField(default=1)
    menu_item_limit = models.PositiveIntegerField(default=0)
    branch_limit = models.PositiveIntegerField(default=1)
    storage_limit_mb = models.PositiveIntegerField(default=200)
    features = models.TextField(blank=True, help_text="One feature per line")
    popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "price"]

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        return self.price == 0


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active"
        CANCELLED = "cancelled"
        PAST_DUE = "past_due"

    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField()
    renews_at = models.DateTimeField(null=True, blank=True, help_text="Empty for the free plan (never expires)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant} on {self.plan}"


class SubscriptionInvoice(models.Model):
    """One plan purchase. Paid through the platform's own Razorpay account."""

    class Status(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        FAILED = "failed"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="subscription_invoices")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    razorpay_order_id = models.CharField(max_length=40, unique=True)
    razorpay_payment_id = models.CharField(max_length=40, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
