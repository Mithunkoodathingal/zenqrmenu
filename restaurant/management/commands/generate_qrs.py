
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.conf import settings
from restaurant.models import Table
import qrcode
from io import BytesIO
import boto3
import time

class Command(BaseCommand):
    help = "Generate and upload QR images for Tables that are missing or whose S3 object is missing."

    def handle(self, *args, **options):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
            endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
        )

        media_prefix = getattr(settings, "MEDIAFILES_LOCATION", "media").rstrip('/')
        bucket = settings.AWS_STORAGE_BUCKET_NAME

        qs = Table.objects.all()
        total = qs.count()
        self.stdout.write(f"Found {total} tables. Processing...")

        for idx, t in enumerate(qs, start=1):
            try:
                close_old_connections()
                key_in_db = t.qr_code.name if getattr(t, "qr_code", None) else None
                needs_upload = True

                if key_in_db:
                    try:
                        s3.head_object(Bucket=bucket, Key=key_in_db)
                        needs_upload = False
                        self.stdout.write(f"[{idx}/{total}] Exists: {key_in_db}")
                    except Exception:
                        needs_upload = True

                if needs_upload:
                    img = qrcode.make(f"https://your-site.com/restaurant/{t.restaurant.id}/table/{t.table_number}")
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    buf.seek(0)
                    key = f"{media_prefix}/qr_codes/restaurant_{t.restaurant.id}/table_{t.table_number}_qr.png"

                    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue(), ContentType="image/png")

                    with transaction.atomic():
                        t.qr_code.name = key
                        t.save(update_fields=['qr_code'])
                    self.stdout.write(f"[{idx}/{total}] Uploaded: {key}")

                time.sleep(0.05)
            except Exception as exc:
                self.stderr.write(f"[{idx}/{total}] Error for Table id={getattr(t,'id',None)}: {exc}")
                continue

        self.stdout.write("Done.")

