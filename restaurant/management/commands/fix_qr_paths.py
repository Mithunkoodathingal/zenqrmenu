from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from restaurant.models import Table


class Command(BaseCommand):
    help = "Fix QR code paths (Windows backslashes → S3/R2-safe slashes)"

    def handle(self, *args, **options):
        fixed = 0
        missing = 0

        for t in Table.objects.exclude(qr_code=""):
            old = t.qr_code.name
            new = old.replace("\\", "/")

            if old != new:
                if default_storage.exists(new):
                    t.qr_code.name = new
                    t.save(update_fields=["qr_code"])
                    fixed += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"FIXED: {old} → {new}")
                    )
                else:
                    missing += 1
                    self.stdout.write(
                        self.style.WARNING(f"MISSING IN STORAGE: {new}")
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Total fixed: {fixed}"))
        self.stdout.write(self.style.WARNING(f"Still missing files: {missing}"))
