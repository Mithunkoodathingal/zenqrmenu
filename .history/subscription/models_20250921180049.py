# subscription/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    table_limit = models.PositiveIntegerField(default=1)
    features = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


class Subscription(models.Model):
    restaurant = models.OneToOneField('restaurant.Restaurant', on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    auto_renew = models.BooleanField(default=False)  # <-- NEW

    def activate(self):
        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        self.is_active = True
        self.save()

    def remaining_tables(self):
        from restaurant.models import Table
        return max(self.plan.table_limit - Table.objects.filter(restaurant=self.restaurant).count(), 0)

    # <-- ADD THIS METHOD
    def has_active_subscription(self) -> bool:
        """
        Convenience helper used by views/templates.
        Returns True if subscription is marked active and the end_date is in the future (or today).
        """
        if not self.is_active:
            return False
        if not self.end_date:
            return False
        # use timezone-aware comparison
        return self.end_date >= timezone.now()

    def __str__(self):
        return f"{self.restaurant} - {self.plan}"


class PaymentTransaction(models.Model):  # <-- NEW
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=50, default="created")  # created, paid, failed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.restaurant} - {self.amount} {self.currency} ({self.status})"
