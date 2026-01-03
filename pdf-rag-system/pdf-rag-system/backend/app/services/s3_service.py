"""
S3 Service - AWS S3 storage operations for PDF documents.
"""

import logging
import os
from typing import Optional, BinaryIO, Dict, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)


class S3Service:
    """
    Service for AWS S3 operations.
    Handles PDF upload, download, and management.
    """
    
    def __init__(self):
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'pdf-rag-documents')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Configure boto3 with retry logic
        config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'exponential'
            },
            connect_timeout=5,
            read_timeout=30
        )
        
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            config=config
        )
        
        self.s3_resource = boto3.resource('s3', region_name=self.region)
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        user_id: str,
        content_type: str = 'application/pdf',
        metadata: Dict = None
    ) -> str:
        """
        Upload a file to S3.
        
        Returns the S3 key of the uploaded file.
        """
        # Generate unique S3 key
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        s3_key = f"documents/{user_id}/{timestamp}/{filename}"
        
        # Prepare metadata
        s3_metadata = {
            'user_id': user_id,
            'original_filename': filename,
            'upload_timestamp': datetime.utcnow().isoformat()
        }
        if metadata:
            s3_metadata.update(metadata)
        
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': s3_metadata,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Uploaded file to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        user_id: str,
        content_type: str = 'application/pdf'
    ) -> str:
        """Upload bytes directly to S3."""
        from io import BytesIO
        return self.upload_file(BytesIO(data), filename, user_id, content_type)
    
    def download_file(self, s3_key: str) -> bytes:
        """Download a file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
            
        except ClientError as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise
    
    def download_to_file(self, s3_key: str, local_path: str):
        """Download S3 object to a local file."""
        try:
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            logger.info(f"Downloaded {s3_key} to {local_path}")
            
        except ClientError as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted file from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {str(e)}")
            return False
    
    def delete_files_batch(self, s3_keys: List[str]) -> Dict:
        """Delete multiple files in a single request."""
        try:
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={
                    'Objects': [{'Key': key} for key in s3_keys],
                    'Quiet': False
                }
            )
            
            deleted = [obj['Key'] for obj in response.get('Deleted', [])]
            errors = response.get('Errors', [])
            
            logger.info(f"Batch delete: {len(deleted)} deleted, {len(errors)} errors")
            return {'deleted': deleted, 'errors': errors}
            
        except ClientError as e:
            logger.error(f"Failed batch delete: {str(e)}")
            raise
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        operation: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for secure, temporary access.
        
        Args:
            s3_key: The S3 key of the object
            expiration: URL expiration time in seconds (default: 1 hour)
            operation: 'get_object' for download, 'put_object' for upload
        """
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise
    
    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: str,
        content_type: str = 'application/pdf',
        expiration: int = 3600
    ) -> Dict:
        """
        Generate a presigned URL for direct browser uploads.
        
        Returns dict with 'url' and 's3_key'.
        """
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        s3_key = f"documents/{user_id}/{timestamp}/{filename}"
        
        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
            
            return {
                'upload_url': url,
                's3_key': s3_key,
                'expires_in': expiration
            }
            
        except ClientError as e:
            logger.error(f"Failed to generate upload URL: {str(e)}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_metadata(self, s3_key: str) -> Dict:
        """Get metadata for a file in S3."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'content_length': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'].isoformat(),
                'metadata': response.get('Metadata', {}),
                'etag': response['ETag'].strip('"')
            }
            
        except ClientError as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            raise
    
    def list_user_files(
        self,
        user_id: str,
        prefix: str = None,
        max_keys: int = 1000
    ) -> List[Dict]:
        """List all files for a user."""
        search_prefix = f"documents/{user_id}/"
        if prefix:
            search_prefix += prefix
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            files = []
            
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=search_prefix,
                MaxKeys=max_keys
            ):
                for obj in page.get('Contents', []):
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'filename': obj['Key'].split('/')[-1]
                    })
            
            return files
            
        except ClientError as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise
    
    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy a file within S3."""
        try:
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                Key=dest_key
            )
            logger.info(f"Copied {source_key} to {dest_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to copy file: {str(e)}")
            return False


class S3LifecycleManager:
    """Manage S3 lifecycle policies."""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
    
    def setup_lifecycle_rules(self):
        """Configure lifecycle rules for the bucket."""
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'MoveToGlacierAfter90Days',
                    'Filter': {'Prefix': 'documents/'},
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ]
                },
                {
                    'ID': 'DeleteIncompleteMultipartUploads',
                    'Filter': {'Prefix': ''},
                    'Status': 'Enabled',
                    'AbortIncompleteMultipartUpload': {
                        'DaysAfterInitiation': 7
                    }
                },
                {
                    'ID': 'DeleteTempFilesAfter1Day',
                    'Filter': {'Prefix': 'temp/'},
                    'Status': 'Enabled',
                    'Expiration': {
                        'Days': 1
                    }
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info("Lifecycle rules configured successfully")
            
        except ClientError as e:
            logger.error(f"Failed to configure lifecycle: {str(e)}")
            raise
