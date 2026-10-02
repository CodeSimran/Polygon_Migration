import os
import logging
from django.conf import settings
from .base import BaseStorageProvider
from .azure import AzureStorageProvider
from .s3 import S3StorageProvider
from .local import LocalStorageProvider
from .gdrive import GoogleDriveStorageProvider

logger = logging.getLogger(__name__)

def get_storage_provider() -> BaseStorageProvider:
    """
    Factory function to instantiate the configured cloud storage provider
    based on the STORAGE_PROVIDER environment variable / Django setting.
    """
    provider_type = getattr(settings, 'STORAGE_PROVIDER', os.getenv('STORAGE_PROVIDER', 'azure')).lower().strip()
    logger.info("Initializing storage provider: '%s'", provider_type)

    if provider_type == 'azure':
        return AzureStorageProvider(
            account_url=getattr(settings, 'AZURE_STORAGE_ACCOUNT_URL', os.getenv('AZURE_STORAGE_ACCOUNT_URL', '')),
            container_name=getattr(settings, 'AZURE_CONTAINER_NAME', os.getenv('AZURE_CONTAINER_NAME', 'testcases')),
            tenant_id=getattr(settings, 'AZURE_TENANT_ID', os.getenv('AZURE_TENANT_ID')),
            client_id=getattr(settings, 'AZURE_CLIENT_ID', os.getenv('AZURE_CLIENT_ID')),
            username=getattr(settings, 'AZURE_USERNAME', os.getenv('AZURE_USERNAME')),
            password=getattr(settings, 'AZURE_PASSWORD', os.getenv('AZURE_PASSWORD')),
            connection_string=os.getenv('AZURE_CONNECTION_STRING')
        )

    elif provider_type in ('s3', 'aws'):
        bucket_name = getattr(settings, 'AWS_S3_BUCKET_NAME', os.getenv('AWS_S3_BUCKET_NAME', 'testcases'))
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', os.getenv('AWS_ACCESS_KEY_ID'))
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', os.getenv('AWS_SECRET_ACCESS_KEY'))
        region = getattr(settings, 'AWS_REGION', os.getenv('AWS_REGION', 'us-east-1'))
        endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', os.getenv('AWS_S3_ENDPOINT_URL'))
        return S3StorageProvider(
            bucket_name=bucket_name,
            access_key_id=access_key,
            secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url
        )

    elif provider_type in ('r2', 'cloudflare'):
        account_id = getattr(settings, 'R2_ACCOUNT_ID', os.getenv('R2_ACCOUNT_ID', ''))
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com" if account_id else None
        return S3StorageProvider(
            bucket_name=getattr(settings, 'R2_BUCKET_NAME', os.getenv('R2_BUCKET_NAME', 'testcases')),
            access_key_id=getattr(settings, 'R2_ACCESS_KEY_ID', os.getenv('R2_ACCESS_KEY_ID')),
            secret_access_key=getattr(settings, 'R2_SECRET_ACCESS_KEY', os.getenv('R2_SECRET_ACCESS_KEY')),
            region_name="auto",
            endpoint_url=endpoint_url
        )

    elif provider_type == 'minio':
        endpoint = getattr(settings, 'MINIO_ENDPOINT', os.getenv('MINIO_ENDPOINT', 'localhost:9000'))
        secure = str(getattr(settings, 'MINIO_SECURE', os.getenv('MINIO_SECURE', 'False'))).lower() == 'true'
        protocol = 'https' if secure else 'http'
        endpoint_url = f"{protocol}://{endpoint}"
        return S3StorageProvider(
            bucket_name=getattr(settings, 'MINIO_BUCKET_NAME', os.getenv('MINIO_BUCKET_NAME', 'testcases')),
            access_key_id=getattr(settings, 'MINIO_ACCESS_KEY', os.getenv('MINIO_ACCESS_KEY')),
            secret_access_key=getattr(settings, 'MINIO_SECRET_KEY', os.getenv('MINIO_SECRET_KEY')),
            endpoint_url=endpoint_url
        )

    elif provider_type in ('gdrive', 'googledrive', 'google_drive'):
        credentials_file = getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS_FILE', os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE'))
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', os.getenv('GOOGLE_DRIVE_FOLDER_ID'))
        return GoogleDriveStorageProvider(
            credentials_file=credentials_file,
            folder_id=folder_id
        )

    elif provider_type == 'local':
        local_dir = getattr(settings, 'LOCAL_STORAGE_DIR', os.getenv('LOCAL_STORAGE_DIR'))
        return LocalStorageProvider(base_dir=local_dir)

    else:
        logger.warning("Unknown STORAGE_PROVIDER '%s', falling back to LocalStorageProvider", provider_type)
        return LocalStorageProvider()
