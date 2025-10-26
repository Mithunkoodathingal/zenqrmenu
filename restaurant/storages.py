# restaurant/storages.py
from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except Exception:
    # If django-storages isn't installed (dev), use FileSystemStorage fallback
    from django.core.files.storage import FileSystemStorage

    class S3Boto3Storage:  # dummy stand-in so imports don't crash
        pass

# Use these locations in STORAGES mapping via OPTIONS {"location": "..."}
class StaticS3Storage(S3Boto3Storage if hasattr(S3Boto3Storage, "__mro__") else FileSystemStorage):
    """
    Storage class for static files (S3). For local dev this is FileSystemStorage.
    """
    if hasattr(S3Boto3Storage, "__mro__"):
        location = getattr(settings, "STATICFILES_LOCATION", "static")

class MediaS3Storage(S3Boto3Storage if hasattr(S3Boto3Storage, "__mro__") else FileSystemStorage):
    """
    Storage class for media files (S3). For local dev this is FileSystemStorage.
    """
    if hasattr(S3Boto3Storage, "__mro__"):
        location = getattr(settings, "MEDIAFILES_LOCATION", "media")
