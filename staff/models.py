"""Restaurant staff, their shifts and breaks. A staff member with an email gets their own login."""
from django.conf import settings
from django.db import models

from restaurants.models import Branch, Restaurant

ROLES = ["owner", "manager", "chef", "cashier", "waiter", "delivery_manager", "inventory_manager"]


class StaffMember(models.Model):
    class Shift(models.TextChoices):
        ON = "on_shift"
        OFF = "off_shift"
        BREAK = "on_break"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="staff")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_member")
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60, blank=True)
    employee_id = models.CharField(max_length=30)
    phone = models.CharField(max_length=20, blank=True)
    country_code = models.CharField(max_length=6, default="+91")
    email = models.EmailField(blank=True)
    designation = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=20, default="cashier")
    is_active = models.BooleanField(default=True)
    shift_status = models.CharField(max_length=10, choices=Shift.choices, default=Shift.OFF)
    shift_schedule = models.JSONField(default=dict, blank=True)
    profile_photo = models.ImageField(upload_to="staff/", null=True, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["first_name", "id"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "employee_id"], name="unique_employee_id")]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Attendance(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="attendance")
    attendance_date = models.DateField()
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-clock_in"]


class StaffBreak(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="breaks")
    break_start = models.DateTimeField()
    break_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-break_start"]
