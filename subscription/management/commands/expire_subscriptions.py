from django.core.management.base import BaseCommand
from django.utils import timezone

from subscription.models import Subscription


class Command(BaseCommand):

    help = "Expire subscriptions whose end date has passed"

    def handle(self, *args, **kwargs):

        expired_count = Subscription.objects.filter(
            is_active=True,
            end_date__lte=timezone.now()
        ).update(
            is_active=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired_count} subscriptions"
            )
        )