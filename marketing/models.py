"""Email campaigns. Only diners who opted in (and haven't unsubscribed) ever receive one."""
from django.db import models

from restaurants.models import Restaurant


class Campaign(models.Model):
    class Audience(models.TextChoices):
        ALL = "all_opted_in"
        SELECTED = "selected"
        RECENT = "recent"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=120)
    subject = models.CharField(max_length=150)
    body = models.TextField(max_length=5000)
    audience = models.CharField(max_length=15, choices=Audience.choices, default=Audience.ALL)
    customer_emails = models.JSONField(default=list, blank=True)
    coupon = models.ForeignKey("coupons.Coupon", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    status = models.CharField(max_length=10, default="draft")
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients = models.JSONField(default=list, blank=True)
    skipped = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
