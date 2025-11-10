from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.management import call_command
from subscription.models import Subscription
from restaurant.models import Restaurant
import threading
import datetime
import sys

class Command(BaseCommand):
    help = "Set a subscription (by restaurant id) to expire after N minutes and optionally run process_subscriptions at expiry."

    def add_arguments(self, parser):
        parser.add_argument('--restaurant-id', type=int, required=True, help='Restaurant id whose subscription should be scheduled for expiry.')
        parser.add_argument('--minutes', type=int, default=5, help='Minutes from now when the subscription should expire (default: 5).')
        parser.add_argument('--simulate-payment', action='store_true', help='When expiry occurs, call process_subscriptions with --simulate-payment to auto-renew (dev/testing only).')
        parser.add_argument('--run-immediately', action='store_true', help='After setting the expiry time, also immediately run process_subscriptions once (dry-run).')

    def handle(self, *args, **options):
        rest_id = options['restaurant_id']
        minutes = options['minutes']
        simulate = options['simulate_payment']
        run_immediately = options['run_immediately']

        restaurant = Restaurant.objects.filter(id=rest_id).first()
        if not restaurant:
            self.stderr.write(f"No restaurant with id={rest_id}")
            sys.exit(1)

        sub = Subscription.objects.filter(restaurant=restaurant).order_by('-id').first()
        if not sub:
            self.stderr.write(f"No subscription found for restaurant id={rest_id}")
            sys.exit(1)

        now = timezone.now()
        expiry_time = now + datetime.timedelta(minutes=minutes)

        sub.end_date = expiry_time
        sub.is_active = True
        sub.save(update_fields=['end_date', 'is_active'])
        self.stdout.write(f"Subscription id={sub.id} for restaurant id={rest_id} set to expire at {expiry_time} (now={now}).")

        if run_immediately:
            self.stdout.write("Running process_subscriptions --dry-run now (immediate) ...")
            call_command('process_subscriptions', '--dry-run')

        def on_expiry():
            self.stdout.write(f"Expiry time reached ({expiry_time}). Running process_subscriptions (simulate_payment={simulate}) ...")
            if simulate:
                call_command('process_subscriptions', '--simulate-payment')
            else:
                call_command('process_subscriptions')

        delay_seconds = minutes * 60
        timer = threading.Timer(delay_seconds, on_expiry)
        timer.daemon = True
        timer.start()
        self.stdout.write(f"Background timer started for {minutes} minute(s). Keep this terminal open.")
