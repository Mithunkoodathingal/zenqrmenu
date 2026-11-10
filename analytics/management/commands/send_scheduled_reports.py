"""Email every scheduled report that is due. Run hourly (cron / Render cron job)."""
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.utils import timezone

from analytics.models import ScheduledReport
from analytics.reports import build


class Command(BaseCommand):
    help = "Send scheduled reports that are due"

    def handle(self, *args, **opts):
        now = timezone.now()
        sent = 0
        for s in ScheduledReport.objects.filter(enabled=True, destination="email", next_run_at__lte=now).select_related("restaurant"):
            request = RequestFactory().get("/")
            request.user = s.restaurant.owner  # owner scope: every branch
            request.query_params = {}
            data = {"from": (now - s.period).isoformat(), "to": now.isoformat()}
            content, mime = build(request, s.restaurant, s.type, s.format, data)
            msg = EmailMessage(f"{s.restaurant.name}: {s.frequency} {s.type} report", "Your scheduled report is attached.",
                               settings.DEFAULT_FROM_EMAIL, [s.email])
            msg.attach(f"{s.type}-{timezone.localdate().isoformat()}.{s.format}", content, mime)
            try:
                msg.send()
            except Exception as e:  # pragma: no cover - depends on the mail provider
                self.stderr.write(f"Report {s.id} failed: {e}")
                continue
            s.last_run_at = now
            s.schedule_next(now)
            s.save(update_fields=["last_run_at", "next_run_at"])
            sent += 1
        self.stdout.write(f"Sent {sent} report(s).")
