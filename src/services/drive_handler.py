import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from src.logger import get_logger

logger = get_logger(__name__)

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
                logger.warning("인증 파일(mycreds.txt)이 없습니다. 드라이브 기능을 비활성화합니다.")
                return
            
            if gauth.access_token_expired:
                logger.info("Drive 토큰이 만료되어 갱신을 시도합니다...")
                gauth.Refresh()
                gauth.SaveCredentialsFile("/app/mycreds.txt") # 갱신된 토큰 저장
                logger.info("Drive 토큰 갱신 및 파일 저장 완료.")
            else:
                gauth.Authorize()
            
            self.drive = GoogleDrive(gauth)
            logger.info("Google Drive 로그인 성공!")
            self._get_or_create_folder()
        except Exception:
            logger.error("Google Drive 로그인 실패", exc_info=True)

    def _get_or_create_folder(self):
        if not self.drive: return
        try:
            file_list = self.drive.ListFile({'q': f"title='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
            if file_list:
                self.folder_id = file_list[0]['id']
                logger.info(f"폴더 연결됨: {self.folder_name} ({self.folder_id})")
            else:
                folder = self.drive.CreateFile({'title': self.folder_name, 'mimeType': 'application/vnd.google-apps.folder'})
                folder.Upload()
                self.folder_id = folder['id']
                logger.info(f"새 폴더 생성됨: {self.folder_name} ({self.folder_id})")
        except Exception:
            logger.error("구글 드라이브 폴더 조회/생성 중 에러 발생", exc_info=True)

    def upload(self, filepath, title):
        if not self.drive or not self.folder_id: 
            logger.warning(f"드라이브가 연결되지 않아 업로드를 건너뜁니다: {title}")
            return False
        try:
            filename = os.path.basename(filepath)
            file_drive = self.drive.CreateFile({
                'title': filename,
                'parents': [{'id': self.folder_id}]
            })
            file_drive.SetContentFile(filepath)
            file_drive.Upload()
            logger.info(f"📤 Drive 업로드 성공: {filename}")
            return True
        except Exception:
            logger.error(f"❌ Drive 업로드 실패: {os.path.basename(filepath)}", exc_info=True)
            return False
