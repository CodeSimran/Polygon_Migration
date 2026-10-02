import logging
import boto3
from botocore.exceptions import ClientError
from typing import Union, List
from .base import BaseStorageProvider

logger = logging.getLogger(__name__)

class S3StorageProvider(BaseStorageProvider):
    """
    S3-compatible storage provider supporting AWS S3, Cloudflare R2, MinIO, and Ceph.
    """
    def __init__(self, bucket_name: str, access_key_id: str = None, secret_access_key: str = None,
                 region_name: str = "us-east-1", endpoint_url: str = None):
        self.bucket_name = bucket_name
        
        session = boto3.session.Session()
        kwargs = {
            'service_name': 's3',
            'region_name': region_name,
        }
        if access_key_id and secret_access_key:
            kwargs['aws_access_key_id'] = access_key_id
            kwargs['aws_secret_access_key'] = secret_access_key
        if endpoint_url:
            kwargs['endpoint_url'] = endpoint_url

        self.client = session.client(**kwargs)
        logger.info("S3 client initialized for bucket '%s' (endpoint: %s)", bucket_name, endpoint_url or "AWS default")

    def upload_file(self, path: str, content: Union[bytes, str]) -> bool:
        try:
            if isinstance(content, str):
                data = content.encode('utf-8')
            else:
                data = content
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=data
            )
            logger.info(f"[S3] Uploaded {len(data)} bytes to {path}")
            return True
        except ClientError as e:
            logger.error(f"[S3] ClientError uploading {path}: {e}")
            return False
        except Exception as e:
            logger.error(f"[S3] Failed to upload {path}: {e}")
            return False

    def delete_problem_files(self, db_problem_id: Union[str, int]) -> bool:
        prefix = f"test_cases/{db_problem_id}/"
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            deleted_count = 0
            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        self.client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects}
                        )
                        deleted_count += len(objects)
            logger.info(f"[S3] Deleted {deleted_count} objects with prefix '{prefix}'")
            return True
        except Exception as e:
            logger.error(f"[S3] Failed to delete objects for prefix '{prefix}': {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            keys = []
            for page in pages:
                if 'Contents' in page:
                    keys.extend([obj['Key'] for obj in page['Contents']])
            return keys
        except Exception as e:
            logger.error(f"[S3] Failed to list objects for prefix '{prefix}': {e}")
            return []
