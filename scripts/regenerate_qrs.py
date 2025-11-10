# scripts/regenerate_qrs.py
import os
import django

# ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant_qr.settings")
django.setup()

from io import BytesIO
import qrcode
from django.core.files.base import ContentFile
from django.conf import settings
from restaurant.models import Table
from django.core.files.storage import default_storage

media_prefix = getattr(settings, "MEDIAFILES_LOCATION", None) or "media"
media_prefix = str(media_prefix).rstrip("/")

def public_url_for(key):
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if bucket:
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return default_storage.url(key)

def ensure_qr_for_table(t, force=False):
    key = f"{media_prefix}/qr_codes/restaurant_{t.restaurant.id}/table_{t.table_number}_qr.png"
    try:
        exists = default_storage.exists(key)
    except Exception:
        exists = False

    if exists and not force:
        return key, public_url_for(key), False

    # generate QR
    target = f"https://zenqrmenu.com/restaurant/{t.restaurant.id}/table/{t.table_number}"
    img = qrcode.make(target)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    content = ContentFile(buf.read())
    saved_name = default_storage.save(key, content)

    t.qr_code.name = saved_name
    t.save(update_fields=["qr_code"])

    return saved_name, public_url_for(saved_name), True

def main():
    tables = list(Table.objects.all())
    print("Found", len(tables), "tables")
    for idx, t in enumerate(tables, start=1):
        key, url, created = ensure_qr_for_table(t, force=False)
        print(f"[{idx}/{len(tables)}] table id={t.id} rest={t.restaurant.id} table_no={t.table_number}")
        print("   saved key:", key)
        print("   public url:", url)
        print("   created:", created)
        print()

if __name__ == "__main__":
    main()
