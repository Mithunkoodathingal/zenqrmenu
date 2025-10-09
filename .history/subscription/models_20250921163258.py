# subscription/

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from datetime import timedelta

class SubscriptionPlan(models.Model):
    """Different subscription plans for restaurants"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    duration_days = models.IntegerField(default=30)  # Subscription duration
    features = models.TextField(blank=True)
    table_limit = models.IntegerField()  # Max tables allowed for this plan

    def __str__(self):
        return self.name

class Subscription(models.Model):
    """Tracks the subscription of a restaurant"""
    restaurant = models.OneToOneField('restaurant.Restaurant', on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def activate(self):
        """Activate subscription upon payment"""
        self.start_date = now()
        self.end_date = now() + timedelta(days=self.plan.duration_days)
        self.is_active = True
        self.save()

    def remaining_tables(self):
        """Return the remaining tables that can be created."""
        if self.plan:
            return self.plan.table_limit - self.restaurant.table_set.count()
        return 0

    def has_active_subscription(self):
        """Check if the subscription is still valid"""
        return self.is_active and self.end_date > now()

    def __str__(self):
        return f"{self.restaurant.name} - {self.plan.name} (Active: {self.is_active})"
