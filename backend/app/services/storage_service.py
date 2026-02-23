import io
import logging
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    parsed = urlparse(settings.MINIO_ENDPOINT)
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def ensure_bucket():
    """Create the bucket if it doesn't exist."""
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
        logger.info(f"Bucket '{settings.MINIO_BUCKET}' already exists")
    except ClientError:
        client.create_bucket(Bucket=settings.MINIO_BUCKET)
        logger.info(f"Created bucket '{settings.MINIO_BUCKET}'")


def upload_file(file_data: bytes, key: str, content_type: str = "application/pdf") -> str:
    """Upload file bytes to MinIO. Returns the object key."""
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=key,
        Body=io.BytesIO(file_data),
        ContentLength=len(file_data),
        ContentType=content_type,
    )
    return key


def download_file(key: str) -> bytes:
    """Download a file from MinIO. Returns raw bytes."""
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
    return response["Body"].read()


def make_statement_key(client_id: str, statement_id: str, filename: str) -> str:
    """Build the S3 key for a bank statement."""
    return f"{client_id}/bank-statements/{statement_id}/{filename}"


def make_invoice_key(client_id: str, invoice_id: str, filename: str) -> str:
    """Build the S3 key for an invoice."""
    return f"{client_id}/invoices/{invoice_id}/{filename}"


def get_presigned_url(object_name: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading an object (1hr default)."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": object_name},
        ExpiresIn=expires_in,
    )
