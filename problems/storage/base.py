from abc import ABC, abstractmethod
import logging
from typing import Optional, List, Union

logger = logging.getLogger(__name__)

class BaseStorageProvider(ABC):
    """
    Abstract base class defining the cloud storage provider interface.
    All storage providers (Azure, S3, R2, GCS, GDrive, Local) must implement these methods.
    """

    @abstractmethod
    def upload_file(self, path: str, content: Union[bytes, str]) -> bool:
        """
        Upload a single file/blob to the given storage path.
        
        Args:
            path: Target storage path (e.g. "test_cases/1/01")
            content: Content as bytes or string
        """
        pass

    def upload_test_case(self, db_problem_id: Union[str, int], test_number: int, input_data: str, output_data: str) -> bool:
        """
        Uploads test case input and output files following the standard structure:
          test_cases/{db_problem_id}/{test_number:02d}
          test_cases/{db_problem_id}/{test_number:02d}.a
        """
        input_path = f"test_cases/{db_problem_id}/{test_number}"
        output_path = f"test_cases/{db_problem_id}/{test_number}.a"
        
        ok_in = self.upload_file(input_path, input_data)
        ok_out = self.upload_file(output_path, output_data)
        return ok_in and ok_out

    @abstractmethod
    def delete_problem_files(self, db_problem_id: Union[str, int]) -> bool:
        """
        Deletes all stored test case files and custom checkers for a given problem ID.
        Prefix: test_cases/{db_problem_id}/
        """
        pass

    def upload_custom_checker(self, db_problem_id: Union[str, int], filename: str, content: Union[bytes, str]) -> bool:
        """
        Uploads a compiled or source custom checker file.
        Path: test_cases/{db_problem_id}/{filename}
        """
        path = f"test_cases/{db_problem_id}/{filename}"
        return self.upload_file(path, content)

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List all file paths matching the given prefix.
        """
        pass
