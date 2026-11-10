"""Delivery partners (riders), which orders they carry, and where they are."""
from django.conf import settings
from django.db import models

from restaurants.models import Restaurant

VEHICLES = ["bike", "scooter", "cycle", "car"]


class DeliveryPartner(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="delivery_partners")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="delivery_partner")
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    vehicle_type = models.CharField(max_length=10, blank=True)
    vehicle_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to="delivery/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy_m = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["first_name", "id"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "phone"], name="unique_partner_phone")]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class DeliveryAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned"
        STARTED = "started"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="delivery_assignments")
    partner = models.ForeignKey(DeliveryPartner, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ASSIGNED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [models.UniqueConstraint(fields=["order"], condition=models.Q(status__in=["assigned", "started"]),
                                               name="one_active_assignment_per_order")]
