from django.core.management.base import BaseCommand

from subscriptions.models import Plan

# Starting plans. Prices are placeholders: change them any time in the admin (/admin/).
PLANS = [
    {"name": "Free", "price": 0, "duration_days": 0, "table_limit": 1, "menu_item_limit": 0, "branch_limit": 0, "position": 0,
     "features": "1 table QR code\nUnlimited menu items\nDine-in ordering"},
    {"name": "Basic", "price": 299, "duration_days": 30, "table_limit": 10, "menu_item_limit": 0, "branch_limit": 0, "position": 1,
     "features": "10 table QR codes\nPickup & delivery ordering\nOnline payments"},
    {"name": "Standard", "price": 599, "duration_days": 30, "table_limit": 20, "menu_item_limit": 0, "branch_limit": 0, "position": 2,
     "popular": True, "features": "20 table QR codes\nKitchen display\nInventory & recipes\nCoupons & marketing"},
    {"name": "Enterprise", "price": 1499, "duration_days": 30, "table_limit": 100, "menu_item_limit": 0, "branch_limit": 0, "position": 3,
     "features": "100 table QR codes\nMultiple branches\nAnalytics & reports\nPriority support"},
]


class Command(BaseCommand):
    help = "Create the starting subscription plans (existing plans are left unchanged)."

    def handle(self, *args, **options):
        for row in PLANS:
            Plan.objects.get_or_create(name=row["name"], defaults=row)
        self.stdout.write("Plans seeded.")
