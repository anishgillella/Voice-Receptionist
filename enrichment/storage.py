"""S3 storage for enrichment results and task artifacts."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from .config import get_enrichment_settings
from .models import TaskResultsResponse, TaskResult

logger = logging.getLogger(__name__)


class EnrichmentResultsStorage:
    """Store and retrieve enrichment results from S3."""

    def __init__(self):
        """Initialize S3 client with AWS credentials from environment."""
        from .config import get_enrichment_settings
        settings = get_enrichment_settings()
        
        # Get AWS credentials from voice_agent config if available
        from voice_agent.app.config import get_settings
        try:
            va_settings = get_settings()
            aws_key = getattr(va_settings, 'aws_access_key_id', None)
            aws_secret = getattr(va_settings, 'aws_secret_access_key', None)
            aws_region = getattr(va_settings, 'aws_region', 'us-east-1')
            bucket_name = getattr(va_settings, 'aws_s3_bucket_name', None)
        except:
            # Fallback to enrichment settings
            aws_key = None
            aws_secret = None
            aws_region = 'us-east-1'
            bucket_name = None

        # If not found in voice_agent, try email_agent
        if not aws_key or not aws_secret or not bucket_name:
            try:
                from email_agent.config import email_settings
                aws_key = email_settings.aws_access_key_id
                aws_secret = email_settings.aws_secret_access_key
                aws_region = email_settings.aws_region
                bucket_name = email_settings.aws_s3_bucket_name
            except:
                raise ValueError("AWS credentials not found in any config")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=aws_region,
        )
        self.bucket_name = bucket_name
        self.region = aws_region

    def get_s3_url(self, s3_key: str) -> str:
        """Generate S3 URL for a given key."""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

    def build_s3_key(
        self,
        customer_id: str,
        task_id: str,
        filename: str,
    ) -> str:
        """Build S3 key path for enrichment results.
        
        Format: customers/{customer_id}/enrichment/{task_id}/{filename}
        """
        return f"customers/{customer_id}/enrichment/{task_id}/{filename}"

    async def store_results(
        self,
        results: TaskResultsResponse,
        customer_id: str,
        task_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store enrichment results in S3.
        
        Args:
            results: TaskResultsResponse with enrichment results
            customer_id: Customer ID for folder structure
            task_name: Optional custom task name (defaults to task_id)
            
        Returns:
            Dict with storage details and S3 URL
        """
        task_id = results.task_id
        filename = task_name or f"enrichment_results_{task_id}.json"
        s3_key = self.build_s3_key(customer_id, task_id, filename)
        
        # Convert results to JSON with datetime serialization
        results_dict = {
            "task_id": results.task_id,
            "status": results.status.value,
            "completed_count": results.completed_count,
            "failed_count": results.failed_count,
            "completed_at": results.completed_at.isoformat() if results.completed_at else None,
            "results": [
                {
                    "item_id": r.item_id,
                    "status": r.status.value,
                    "enriched_data": r.enriched_data,
                    "raw_result": r.raw_result,
                    "error": r.error,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in results.results
            ],
            "stored_at": datetime.utcnow().isoformat(),
        }
        
        json_content = json.dumps(results_dict, indent=2)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode("utf-8"),
                ContentType="application/json",
                Metadata={
                    "task_id": task_id,
                    "customer_id": customer_id,
                    "completed_count": str(results.completed_count),
                    "failed_count": str(results.failed_count),
                },
            )
            
            s3_url = self.get_s3_url(s3_key)
            logger.info(f"Stored enrichment results at: {s3_url}")
            
            return {
                "s3_key": s3_key,
                "s3_url": s3_url,
                "filename": filename,
                "task_id": task_id,
                "customer_id": customer_id,
                "completed_count": results.completed_count,
                "failed_count": results.failed_count,
                "stored_at": datetime.utcnow().isoformat(),
            }
            
        except ClientError as e:
            logger.error(f"Failed to store results in S3: {e}")
            raise

    async def retrieve_results(
        self,
        customer_id: str,
        task_id: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve stored enrichment results from S3.
        
        Args:
            customer_id: Customer ID
            task_id: Task ID
            filename: Optional filename (defaults to default naming)
            
        Returns:
            Dict with stored results
        """
        filename = filename or f"enrichment_results_{task_id}.json"
        s3_key = self.build_s3_key(customer_id, task_id, filename)
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response["Body"].read().decode("utf-8")
            results = json.loads(content)
            
            logger.info(f"Retrieved enrichment results from: {s3_key}")
            return results
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Results not found at: {s3_key}")
                return {}
            logger.error(f"Failed to retrieve results from S3: {e}")
            raise

    async def list_results(
        self,
        customer_id: str,
    ) -> list[Dict[str, Any]]:
        """List all enrichment results for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of dicts with S3 objects
        """
        prefix = f"customers/{customer_id}/enrichment/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )
            
            if "Contents" not in response:
                return []
            
            results = []
            for obj in response["Contents"]:
                results.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "url": self.get_s3_url(obj["Key"]),
                })
            
            logger.info(f"Found {len(results)} enrichment results for customer {customer_id}")
            return results
            
        except ClientError as e:
            logger.error(f"Failed to list results from S3: {e}")
            raise

    async def delete_results(
        self,
        customer_id: str,
        task_id: str,
        filename: Optional[str] = None,
    ) -> bool:
        """Delete stored enrichment results from S3.
        
        Args:
            customer_id: Customer ID
            task_id: Task ID
            filename: Optional filename (defaults to default naming)
            
        Returns:
            True if successful
        """
        filename = filename or f"enrichment_results_{task_id}.json"
        s3_key = self.build_s3_key(customer_id, task_id, filename)
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted enrichment results: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete results from S3: {e}")
            return False
