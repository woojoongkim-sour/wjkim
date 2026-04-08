import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings
import logging
from typing import Optional
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            except ClientError as e:
                logger.warning(f"Could not create bucket: {e}")

    def _generate_key(self, customer_id: int, category: str, filename: str) -> str:
        unique_id = uuid.uuid4().hex[:8]
        suffix = Path(filename).suffix.lower()
        return f"customers/{customer_id}/{category}/{unique_id}{suffix}"

    async def upload_file(
        self,
        file_content: bytes,
        customer_id: int,
        category: str,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        key = self._generate_key(customer_id, category, filename)
        
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args,
            )
            logger.info(f"Uploaded file: {key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    async def download_file(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            raise

    async def delete_file(self, key: str):
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted file: {key}")
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            raise

    async def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def file_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False


# Singleton instance
storage = S3Storage()


async def get_storage() -> S3Storage:
    return storage
