"""Restaurant-side alerts (new orders, status changes, payment problems) and how the owner wants to hear about them."""
from django.db import models

from restaurants.models import Restaurant

TYPES = ["order_received", "order_confirmed", "order_preparing", "order_ready", "order_out_for_delivery",
         "order_delivered", "refund_completed", "payment_failed", "system"]


class Notification(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, default="system")
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=500, blank=True)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["restaurant", "-created_at"])]


class NotificationPreferences(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name="notification_preferences")
    browser_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    email_address = models.EmailField(blank=True)
    whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    push_enabled = models.BooleanField(default=False)
    events = models.JSONField(default=dict, blank=True)

    def wants(self, kind):
        return self.events.get(kind, True) is not False
