"""Kitchen display extras: ticket priority and kitchen notes. The order's own status stays the single source of truth."""
from django.db import models

from restaurants.models import Restaurant

PRIORITIES = ["low", "normal", "high", "urgent"]


class KitchenTicket(models.Model):
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="kitchen_ticket")
    priority = models.CharField(max_length=10, default="normal")
    updated_at = models.DateTimeField(auto_now=True)


class KitchenNote(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="kitchen_notes")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, null=True, blank=True, related_name="kitchen_notes")
    note = models.TextField()
    note_type = models.CharField(max_length=20, default="kitchen")
    is_internal = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
