from django.core.management.base import BaseCommand
from restaurant.models import Table
from restaurant.views import generate_qr_code
from django.conf import settings


class Command(BaseCommand):
    help = "Regenerate missing QR code images and upload them to storage"

    def handle(self, *args, **options):
        regenerated = 0

        for t in Table.objects.all():
            if not t.qr_code:
                continue

            key = t.qr_code.name.replace("\\", "/")

            try:
                exists = t.qr_code.storage.exists(key)
            except Exception:
                exists = False

            if not exists:
                self.stdout.write(
                    self.style.WARNING(
                        f"Regenerating QR for Table {t.id} ({key})"
                    )
                )
                try:
                    generate_qr_code(t, force=True)
                    regenerated += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"FAILED for Table {t.id}: {e}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Total regenerated: {regenerated}")
        )
