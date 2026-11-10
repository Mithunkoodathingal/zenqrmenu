"""Diner reviews: one per completed order, verified diners only.

Diners edit for 7 days and may delete any time; owners reply or hide (never delete); admins remove from Django admin."""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from restaurants.models import Restaurant

EDIT_DAYS = 7


class Review(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="reviews")
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="review")
    customer = models.ForeignKey("customers.CustomerProfile", on_delete=models.CASCADE, related_name="reviews")
    customer_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, max_length=1000)
    owner_response = models.TextField(blank=True, max_length=1000)
    owner_responded_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True, help_text="Owner switch: hide or show on the public page.")
    removed_by_admin = models.BooleanField(default=False, help_text="Admin moderation: removed reviews never show.")
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def editable_until(self):
        return self.created_at + timedelta(days=EDIT_DAYS)

    @property
    def editable(self):
        return timezone.now() <= self.editable_until
