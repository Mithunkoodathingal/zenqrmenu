# restaurant/storages.py
from storages.backends.s3boto3 import S3Boto3Storage

class StaticS3Storage(S3Boto3Storage):
    default_acl = None
    file_overwrite = False
    location = "static"  # overridden by STORAGES OPTIONS if provided
    querystring_auth = False

class MediaS3Storage(S3Boto3Storage):
    default_acl = None
    file_overwrite = False
    location = "media"  # overridden by STORAGES OPTIONS if provided
    querystring_auth = False
