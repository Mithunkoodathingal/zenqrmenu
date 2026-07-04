# restaurant/utils/s3.py
import boto3
from django.conf import settings

def get_s3_client():
    """
    Return an S3 client. Only include endpoint_url when it's set (non-empty / non-None).
    This prevents botocore ValueError on empty endpoint strings.
    """
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None
    kwargs = {
        "aws_access_key_id": getattr(settings, "AWS_ACCESS_KEY_ID", None),
        "aws_secret_access_key": getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        "region_name": getattr(settings, "AWS_S3_REGION_NAME", None),
    }
    if endpoint:
        return boto3.client("s3", endpoint_url=endpoint, **kwargs)
    return boto3.client("s3", **kwargs)
