import os
import shutil
import logging
from typing import Union, List
from pathlib import Path
from .base import BaseStorageProvider

logger = logging.getLogger(__name__)

class LocalStorageProvider(BaseStorageProvider):
    """
    Local filesystem storage provider that mirrors the exact directory structure:
    test_cases/{problem_id}/{test_number} and test_cases/{problem_id}/{test_number}.a
    """
    def __init__(self, base_dir: str = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(os.getcwd()) / "media" / "cloud_storage"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageProvider initialized at '%s'", self.base_dir)

    def upload_file(self, path: str, content: Union[bytes, str]) -> bool:
        try:
            full_path = self.base_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(content, str):
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(full_path, "wb") as f:
                    f.write(content)
            logger.info(f"[Local] Saved file to {full_path}")
            return True
        except Exception as e:
            logger.error(f"[Local] Failed to save {path}: {e}")
            return False

    def delete_problem_files(self, db_problem_id: Union[str, int]) -> bool:
        try:
            target_dir = self.base_dir / "test_cases" / str(db_problem_id)
            if target_dir.exists():
                shutil.rmtree(target_dir)
                logger.info(f"[Local] Deleted directory {target_dir}")
            return True
        except Exception as e:
            logger.error(f"[Local] Failed to delete directory for problem {db_problem_id}: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            target_path = self.base_dir / prefix
            if not target_path.exists():
                return []
            if target_path.is_file():
                return [prefix]
            return [str(p.relative_to(self.base_dir)).replace("\\", "/") for p in target_path.rglob("*") if p.is_file()]
        except Exception as e:
            logger.error(f"[Local] Failed to list files for prefix '{prefix}': {e}")
            return []
