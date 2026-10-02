import os
import shutil
import tempfile
from django.test import TestCase, override_settings
from problems.storage import (
    BaseStorageProvider,
    LocalStorageProvider,
    S3StorageProvider,
    AzureStorageProvider,
    get_storage_provider
)

class StorageAbstractionTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_local_storage_upload_and_delete(self):
        provider = LocalStorageProvider(base_dir=self.temp_dir)
        
        # Test upload test case
        success = provider.upload_test_case(
            db_problem_id=99,
            test_number=1,
            input_data="4 5\n",
            output_data="9\n"
        )
        self.assertTrue(success)
        
        # Check files exist
        in_file = os.path.join(self.temp_dir, "test_cases", "99", "01")
        out_file = os.path.join(self.temp_dir, "test_cases", "99", "01.a")
        self.assertTrue(os.path.exists(in_file))
        self.assertTrue(os.path.exists(out_file))
        
        with open(in_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "4 5\n")
        with open(out_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "9\n")

        # Test upload custom checker
        provider.upload_custom_checker(99, "custom_checker.cpp", "int main() { return 0; }")
        checker_file = os.path.join(self.temp_dir, "test_cases", "99", "custom_checker.cpp")
        self.assertTrue(os.path.exists(checker_file))

        # Test list files
        files = provider.list_files("test_cases/99")
        self.assertEqual(len(files), 3)

        # Test delete problem files
        del_success = provider.delete_problem_files(99)
        self.assertTrue(del_success)
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "test_cases", "99")))

    @override_settings(STORAGE_PROVIDER='local')
    def test_factory_local(self):
        provider = get_storage_provider()
        self.assertIsInstance(provider, LocalStorageProvider)

    @override_settings(
        STORAGE_PROVIDER='s3',
        AWS_S3_BUCKET_NAME='test-bucket',
        AWS_ACCESS_KEY_ID='mock-key',
        AWS_SECRET_ACCESS_KEY='mock-secret',
        AWS_REGION='us-east-1'
    )
    def test_factory_s3(self):
        provider = get_storage_provider()
        self.assertIsInstance(provider, S3StorageProvider)
        self.assertEqual(provider.bucket_name, 'test-bucket')
