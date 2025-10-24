"""AWS S3 client for document storage."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from .config import email_settings

logger = logging.getLogger(__name__)


class S3Client:
    """Client for interacting with AWS S3."""

    def __init__(self):
        """Initialize S3 client with AWS credentials."""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=email_settings.aws_access_key_id,
            aws_secret_access_key=email_settings.aws_secret_access_key,
            region_name=email_settings.aws_region,
        )
        self.bucket_name = email_settings.aws_s3_bucket_name
        self.region = email_settings.aws_region

    def get_s3_url(self, s3_key: str) -> str:
        """Generate S3 URL for a given key."""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

    def build_s3_key(
        self,
        first_name: str,
        last_name: str,
        email_id: str,
        filename: str,
    ) -> str:
        """Build S3 key path following the folder structure."""
        # Format: customers/{first_name}_{last_name}/emails/{email_id}/{filename}
        customer_folder = f"{first_name}_{last_name}".replace(" ", "_").lower()
        return f"customers/{customer_folder}/emails/{email_id}/{filename}"

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        first_name: str,
        last_name: str,
        email_id: str,
        mime_type: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Upload a document to S3.

        Returns:
            Tuple of (s3_key, s3_url, error_message)
        """
        try:
            s3_key = self.build_s3_key(
                first_name=first_name,
                last_name=last_name,
                email_id=email_id,
                filename=filename,
            )

            extra_args = {}
            if mime_type:
                extra_args["ContentType"] = mime_type

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                **extra_args,
            )

            s3_url = self.get_s3_url(s3_key)

            logger.info(f"Successfully uploaded {filename} to S3: {s3_key}")
            return s3_key, s3_url, None

        except ClientError as error:
            error_message = f"Error uploading to S3: {error}"
            logger.error(error_message)
            return None, None, error_message
        except Exception as error:
            error_message = f"Unexpected error uploading to S3: {error}"
            logger.error(error_message)
            return None, None, error_message

    async def download_document(self, s3_key: str) -> Optional[bytes]:
        """Download a document from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = response["Body"].read()
            logger.info(f"Successfully downloaded {s3_key} from S3")
            return file_content
        except ClientError as error:
            logger.error(f"Error downloading from S3: {error}")
            return None

    async def delete_document(self, s3_key: str) -> bool:
        """Delete a document from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Successfully deleted {s3_key} from S3")
            return True
        except ClientError as error:
            logger.error(f"Error deleting from S3: {error}")
            return False

    async def list_customer_documents(
        self,
        first_name: str,
        last_name: str,
    ) -> list[dict]:
        """List all documents for a customer."""
        try:
            customer_folder = f"{first_name}_{last_name}".replace(" ", "_").lower()
            prefix = f"customers/{customer_folder}/emails/"

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )

            documents = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    documents.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "url": self.get_s3_url(obj["Key"]),
                        }
                    )

            return documents
        except ClientError as error:
            logger.error(f"Error listing documents from S3: {error}")
            return []
