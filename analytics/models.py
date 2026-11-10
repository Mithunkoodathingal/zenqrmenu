from datetime import timedelta

from django.db import models
from django.utils import timezone

from restaurants.models import Restaurant

REPORT_TYPES = ["payments", "refunds", "orders", "sales", "tax", "customers", "delivery", "staff", "coupons", "menu"]
FORMATS = ["csv", "xlsx", "pdf"]
FREQUENCIES = {"daily": 1, "weekly": 7, "monthly": 30}


class ScheduledReport(models.Model):
    """Emailed by `python manage.py send_scheduled_reports` (run it hourly from cron)."""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="scheduled_reports")
    type = models.CharField(max_length=12)
    format = models.CharField(max_length=4, default="csv")
    frequency = models.CharField(max_length=8, default="weekly")
    destination = models.CharField(max_length=8, default="email")
    email = models.EmailField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def period(self):
        return timedelta(days=FREQUENCIES.get(self.frequency, 7))

    def schedule_next(self, base=None):
        self.next_run_at = (base or timezone.now()) + self.period
