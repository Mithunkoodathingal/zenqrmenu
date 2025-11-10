# subscription/management/commands/fastforward_subs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from subscription.models import Subscription
from datetime import timedelta

class Command(BaseCommand):
    help = "Fast-forward subscriptions: subtract given days (or set end_date to now)"

    def add_arguments(self, parser):
        parser.add_argument('--to-now', action='store_true', help='Set all end_date to now (expire immediately)')
        parser.add_argument('--days', type=int, default=0, help='Subtract days from end_date')

    def handle(self, *args, **options):
        if options['to_now']:
            now = timezone.now()
            qs = Subscription.objects.all()
            for s in qs:
                s.end_date = now
                s.save()
            self.stdout.write("All subscriptions set to end now.")
            return

        days = options['days']
        if days:
            qs = Subscription.objects.all()
            for s in qs:
                if s.end_date:
                    s.end_date = s.end_date - timedelta(days=days)
                    s.save()
            self.stdout.write(f"Subcriptions moved back by {days} days.")
            return

        self.stdout.write("No action taken. Use --to-now or --days N")
