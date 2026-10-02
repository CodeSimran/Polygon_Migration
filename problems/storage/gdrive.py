import io
import os
import logging
from typing import Union, List
from .base import BaseStorageProvider

logger = logging.getLogger(__name__)

class GoogleDriveStorageProvider(BaseStorageProvider):
    """
    Google Drive implementation of BaseStorageProvider.
    Uploads and organizes test cases into Google Drive folders.
    Structure:
      [Root Folder] / test_cases / {problem_id} / {test_number}
      [Root Folder] / test_cases / {problem_id} / {test_number}.a
    """

    def __init__(self, credentials_file: str = None, folder_id: str = None):
        self.credentials_file = credentials_file
        self.root_folder_id = folder_id
        self.service = None
        self._folder_cache = {}

        if not self.credentials_file or not os.path.exists(self.credentials_file):
            logger.warning("Google Drive credentials file not found at '%s'. Service will initialize on valid file.", self.credentials_file)
            return

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            SCOPES = ['https://www.googleapis.com/auth/drive']
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize Google Drive service: %s", e)
            raise

    def _get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """
        Helper to find or create a folder under a parent folder in Google Drive.
        """
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        if not self.service:
            raise Exception("Google Drive service is not authenticated.")

        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            folder_id = files[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            logger.info("Created Google Drive folder '%s' (ID: %s)", folder_name, folder_id)

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def upload_file(self, path: str, content: Union[bytes, str]) -> bool:
        """
        Uploads file to Google Drive preserving folder path.
        path example: "test_cases/1/01"
        """
        if not self.service:
            logger.error("Google Drive service not configured.")
            return False

        try:
            from googleapiclient.http import MediaIoBaseUpload

            parts = [p for p in path.replace("\\", "/").split("/") if p]
            filename = parts[-1]
            folder_parts = parts[:-1]

            current_parent_id = self.root_folder_id
            for folder in folder_parts:
                current_parent_id = self._get_or_create_folder(folder, current_parent_id)

            # Check if file already exists to overwrite
            query = f"name='{filename}' and trashed=false"
            if current_parent_id:
                query += f" and '{current_parent_id}' in parents"

            existing = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute().get('files', [])
            
            if isinstance(content, str):
                data = content.encode('utf-8')
            else:
                data = content

            media = MediaIoBaseUpload(io.BytesIO(data), mimetype='application/octet-stream', resumable=True)

            if existing:
                file_id = existing[0]['id']
                self.service.files().update(fileId=file_id, media_body=media).execute()
                logger.info("[GDrive] Updated existing file '%s' (ID: %s)", path, file_id)
            else:
                file_metadata = {'name': filename}
                if current_parent_id:
                    file_metadata['parents'] = [current_parent_id]
                created = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                logger.info("[GDrive] Uploaded new file '%s' (ID: %s)", path, created.get('id'))

            return True
        except Exception as e:
            logger.error("[GDrive] Error uploading %s: %s", path, e)
            return False

    def delete_problem_files(self, db_problem_id: Union[str, int]) -> bool:
        """
        Deletes the problem folder 'test_cases/{db_problem_id}' in Google Drive.
        """
        if not self.service:
            return False

        try:
            test_cases_folder_id = self._get_or_create_folder("test_cases", self.root_folder_id)
            query = f"mimeType='application/vnd.google-apps.folder' and name='{db_problem_id}' and '{test_cases_folder_id}' in parents and trashed=false"
            folders = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute().get('files', [])

            for f in folders:
                self.service.files().delete(fileId=f['id']).execute()
                logger.info("[GDrive] Deleted problem folder '%s' (ID: %s)", db_problem_id, f['id'])
            return True
        except Exception as e:
            logger.error("[GDrive] Error deleting problem folder %s: %s", db_problem_id, e)
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        if not self.service:
            return []
        try:
            query = "trashed=false"
            if self.root_folder_id:
                query += f" and '{self.root_folder_id}' in parents"
            files = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute().get('files', [])
            return [f['name'] for f in files]
        except Exception as e:
            logger.error("[GDrive] Error listing files: %s", e)
            return []
