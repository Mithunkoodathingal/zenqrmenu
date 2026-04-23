# subscription/management/commands/create_plans.py

from django.core.management.base import BaseCommand
from subscription.models import SubscriptionPlan
from decimal import Decimal


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        plans = [
            {"name": "free", "price": Decimal("0.00"), "duration_days": 30, "table_limit": 1},
            {"name": "basic", "price": Decimal("100.00"), "duration_days": 30, "table_limit": 10},
            {"name": "standard", "price": Decimal("200.00"), "duration_days": 30, "table_limit": 20},
            {"name": "enterprise", "price": Decimal("500.00"), "duration_days": 30, "table_limit": 100},
        ]

        for p in plans:
            SubscriptionPlan.objects.update_or_create(
                name=p["name"],
                defaults=p
            )

        self.stdout.write("Plans created/updated successfully")