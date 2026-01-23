import unittest
from unittest.mock import MagicMock, patch
import os
from src.services.drive_handler import DriveUploader

class TestDriveUploadConvert(unittest.TestCase):
    def setUp(self):
        # Mock GoogleAuth and GoogleDrive
        self.mock_gauth_patcher = patch('src.services.drive_handler.GoogleAuth')
        self.mock_drive_patcher = patch('src.services.drive_handler.GoogleDrive')
        
        self.mock_gauth_cls = self.mock_gauth_patcher.start()
        self.mock_drive_cls = self.mock_drive_patcher.start()
        
        # Setup mock instances
        self.mock_gauth = self.mock_gauth_cls.return_value
        self.mock_gauth.credentials = True # Simulate logged in
        self.mock_gauth.access_token_expired = False
        
        self.mock_drive = self.mock_drive_cls.return_value
        
        # Mock folder search to return existing folder
        self.mock_folder_file = MagicMock()
        self.mock_folder_file.__getitem__.side_effect = lambda k: 'folder_id_123' if k == 'id' else None
        self.mock_drive.ListFile.return_value.GetList.return_value = [self.mock_folder_file]

        self.uploader = DriveUploader()
        self.uploader.folder_id = 'folder_id_123' # Force folder ID (though init should set it)

    def tearDown(self):
        self.mock_gauth_patcher.stop()
        self.mock_drive_patcher.stop()

    def test_upload_md_as_gdoc(self):
        # Setup temporary markdown file
        test_filename = "test_doc.md"
        test_content = "# Title\n\n## Section\n- Item 1\n- Item 2"
        with open(test_filename, "w", encoding="utf-8") as f:
            f.write(test_content)

        try:
            # Mock CreateFile
            mock_file_instance = MagicMock()
            self.mock_drive.CreateFile.return_value = mock_file_instance
            
            # Execute upload
            result = self.uploader.upload(test_filename, "Test Document Title")
            
            self.assertTrue(result)
            
            # Verify CreateFile called with correct metadata for source file
            self.mock_drive.CreateFile.assert_called_with({
                'title': 'Test Document Title',
                'parents': [{'id': 'folder_id_123'}],
                'mimeType': 'text/html'
            })
            
            # Verify SetContentFile called instead of SetContentString
            mock_file_instance.SetContentFile.assert_called_once()
            
            # Verify temporary file was created and used, we can't read it as it is deleted
            # But we can verify it was called with a filepath ending in .html
            args, kwargs = mock_file_instance.SetContentFile.call_args
            temp_path = args[0]
            self.assertTrue(temp_path.endswith('.html'))
            
            # Since we can't read the file (it's deleted), we trust the logic if SetContentFile was called
            # and verify Upload with convert=True
            mock_file_instance.Upload.assert_called_once_with(param={'convert': True})
            
        finally:
            if os.path.exists(test_filename):
                os.remove(test_filename)

if __name__ == '__main__':
    unittest.main()
