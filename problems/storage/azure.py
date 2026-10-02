import logging
from typing import Union, List
from azure.identity import UsernamePasswordCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ClientAuthenticationError
from .base import BaseStorageProvider

logger = logging.getLogger(__name__)

class AzureStorageProvider(BaseStorageProvider):
    """
    Azure Blob Storage implementation of BaseStorageProvider.
    """
    def __init__(self, account_url: str, container_name: str, tenant_id: str = None, 
                 client_id: str = None, username: str = None, password: str = None, connection_string: str = None):
        self.account_url = account_url
        self.container_name = container_name
        self.blob_service_client = None

        try:
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            elif tenant_id and client_id and username and password:
                credential = UsernamePasswordCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    username=username,
                    password=password
                )
                self.blob_service_client = BlobServiceClient(
                    account_url=self.account_url, 
                    credential=credential
                )
            else:
                self.blob_service_client = BlobServiceClient(account_url=self.account_url)
            logger.info("Azure BlobServiceClient initialized successfully for container '%s'", container_name)
        except ClientAuthenticationError as e:
            logger.error(f"Azure authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Azure BlobServiceClient initialization error: {e}")
            raise

    def upload_file(self, path: str, content: Union[bytes, str]) -> bool:
        try:
            if isinstance(content, str):
                data = content.encode('utf-8')
            else:
                data = content
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=path)
            blob_client.upload_blob(data, overwrite=True)
            logger.info(f"[Azure] Uploaded {len(data)} bytes to {path}")
            return True
        except Exception as e:
            logger.error(f"[Azure] Failed to upload {path}: {e}")
            return False

    def delete_problem_files(self, db_problem_id: Union[str, int]) -> bool:
        prefix = f"test_cases/{db_problem_id}/"
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs_to_delete = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
            for blob_name in blobs_to_delete:
                container_client.delete_blob(blob_name)
            logger.info(f"[Azure] Deleted {len(blobs_to_delete)} blobs with prefix '{prefix}'")
            return True
        except Exception as e:
            logger.error(f"[Azure] Failed to delete blobs with prefix '{prefix}': {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            return [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
        except Exception as e:
            logger.error(f"[Azure] Failed to list blobs for prefix '{prefix}': {e}")
            return []
