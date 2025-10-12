# restaurant/storages.py
from storages.backends.s3boto3 import S3Boto3Storage

class StaticS3Storage(S3Boto3Storage):
    default_acl = None
    file_overwrite = False
    # location is provided via STORAGES -> OPTIONS -> {"location": "<prefix>"}
    # optionally set custom cache control
    def __init__(self, *args, **kwargs):
        # if 'location' passed in OPTIONS it will be applied automatically
        super().__init__(*args, **kwargs)


class MediaS3Storage(S3Boto3Storage):
    default_acl = None
    file_overwrite = False
    querystring_auth = False
    # location provided via STORAGES mapping
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
