import boto3
from django.conf import settings
from botocore.exceptions import ClientError


def generate_presigned_post(key, content_type, expiration=3600) -> dict:
    """
    Generate a presigned POST for S3 so clients upload directly to S3
    """
    s3_client = boto3.client(
        "s3",
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
    )

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME")

    try:
        fields = {"Content-Type": content_type, "key": key}
        conditions = [
            {"key": key},
            {"Content-Type": content_type},
            ["content-length-range", 1, 50 * 1024 * 1024 * 10],
            # limit size to 500MB
        ]
        post = s3_client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields=fields,
            Condtions=conditions,
            ExpiresIn=expiration,
        )
    except ClientError as e:
        raise e
    return post
