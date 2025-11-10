# restaurant/storages.py
from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage as _S3Base
    HAS_S3 = True
except Exception:
    from django.core.files.storage import FileSystemStorage as _S3Base
    HAS_S3 = False

class StaticS3Storage(_S3Base):
    location = getattr(settings, "STATICFILES_LOCATION", "static")
    if HAS_S3:
        # do not set default_acl when the bucket enforces ACLs disabled
        file_overwrite = False

class MediaS3Storage(_S3Base):
    location = getattr(settings, "MEDIAFILES_LOCATION", "media")
    if HAS_S3:
        # do not set default_acl
        file_overwrite = False


