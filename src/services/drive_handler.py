import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

class DriveUploader:
    def __init__(self):
        self.drive = None
        self.folder_id = None
        self.folder_name = "NotebookLM_Source"
        self._login()

    def _login(self):
        try:
            gauth = GoogleAuth()
            # Docker 컨테이너 내 경로 지정
            gauth.LoadCredentialsFile("/app/mycreds.txt")
            if gauth.credentials is None:
                print("[Drive] ⚠️ 인증 파일(mycreds.txt)이 없습니다. 드라이브 기능을 비활성화합니다.")
                return
            
            if gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()
            
            self.drive = GoogleDrive(gauth)
            print("[Drive] ✅ Google Drive 로그인 성공!")
            self._get_or_create_folder()
        except Exception as e:
            print(f"[Drive] ❌ 로그인 실패: {e}")

    def _get_or_create_folder(self):
        if not self.drive: return
        try:
            file_list = self.drive.ListFile({'q': f"title='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
            if file_list:
                self.folder_id = file_list[0]['id']
                print(f"[Drive] 폴더 연결됨: {self.folder_name} ({self.folder_id})")
            else:
                folder = self.drive.CreateFile({'title': self.folder_name, 'mimeType': 'application/vnd.google-apps.folder'})
                folder.Upload()
                self.folder_id = folder['id']
                print(f"[Drive] 새 폴더 생성됨: {self.folder_name} ({self.folder_id})")
        except Exception as e:
            print(f"[Drive] 폴더 에러: {e}")

    def upload(self, filepath, title):
        if not self.drive or not self.folder_id: return False
        try:
            filename = os.path.basename(filepath)
            file_drive = self.drive.CreateFile({
                'title': filename,
                'parents': [{'id': self.folder_id}]
            })
            file_drive.SetContentFile(filepath)
            file_drive.Upload()
            print(f"[Drive] 📤 업로드 성공: {filename}")
            return True
        except Exception as e:
            print(f"[Drive] ❌ 업로드 실패: {e}")
            return False
