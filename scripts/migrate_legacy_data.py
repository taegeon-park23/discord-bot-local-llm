import asyncio
import glob
import os
import re
import argparse
import logging
from datetime import datetime
from tqdm.asyncio import tqdm

# Add project root to path
import sys
sys.path.append(os.getcwd())

from src.database.engine import AsyncSessionLocal
from src.database.models import Document, DocType, UploadStatus
from src.services.drive_handler import DriveUploader
from sqlalchemy.future import select

# Logger Setup
logging.basicConfig(
    filename='migration_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console_logger = logging.getLogger('migration')
console_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
console_logger.addHandler(handler)

class Migrator:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.drive = None
        if not dry_run:
            try:
                self.drive = DriveUploader()
                if not self.drive.drive:
                     console_logger.warning("DriveUploader initialized but no Drive connection. Uploads will crash.")
            except Exception as e:
                console_logger.error(f"Failed to init DriveUploader: {e}")

    def parse_metadata(self, filepath):
        filename = os.path.basename(filepath)
        content = ""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return None

        # 1. Doc Type
        doc_type = DocType.SUMMARY
        if "[DeepDive]" in filename:
            doc_type = DocType.DEEP_DIVE
        elif "Weekly_Report" in filename:
            doc_type = DocType.WEEKLY_REPORT

        # 2. Title
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename.replace(".md", "")
        
        # 3. Date (from filename YYYY-MM-DD or creation time)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        created_at = datetime.now()
        if date_match:
            try:
                created_at = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            except: pass
        else:
            created_at = datetime.fromtimestamp(os.path.getctime(filepath))

        return {
            "title": title,
            "doc_type": doc_type,
            "created_at": created_at,
            "local_path": filepath # Store as absolute path? PRD said 'local_file_path'
        }

    async def get_or_create_document(self, session, meta):
        # Check by path
        abs_path = os.path.abspath(meta['local_path'])
        
        query = select(Document).where(Document.local_file_path == abs_path)
        result = await session.execute(query)
        doc = result.scalar_one_or_none()

        if doc:
            return doc, False

        # Create
        new_doc = Document(
            title=meta['title'],
            doc_type=meta['doc_type'],
            local_file_path=abs_path,
            created_at=meta['created_at'],
            updated_at=meta['created_at'],
            gdrive_upload_status=UploadStatus.PENDING
        )
        if not self.dry_run:
            session.add(new_doc)
            await session.commit()
            await session.refresh(new_doc)
        
        return new_doc, True

    async def process_file(self, filepath):
        meta = self.parse_metadata(filepath)
        if not meta:
            logging.error(f"Failed to parse {filepath}")
            return

        action_log = f"[{meta['doc_type'].value}] {meta['title']}"

        async with AsyncSessionLocal() as session:
            try:
                doc, created = await self.get_or_create_document(session, meta)
                
                if self.dry_run:
                    status = "WOULD_CREATE" if created else "EXISTS"
                    console_logger.info(f"[DRY-RUN] DB: {status} | Drive: WOULD_UPLOAD | {action_log}")
                    return

                # DB Logic Real
                if created:
                    console_logger.info(f"[DB] Created: {action_log}")
                
                # Check Drive Status
                if doc.gdrive_upload_status == UploadStatus.SUCCESS and doc.gdrive_file_id:
                    # Already synced
                    return 

                # Drive Logic Real
                if self.drive:
                    # Run sync upload in thread
                    success = await asyncio.to_thread(self.drive.upload, doc.local_file_path, doc.title)
                    
                    if success:
                        doc.gdrive_upload_status = UploadStatus.SUCCESS
                        doc.last_synced_at = datetime.now()
                        # We don't get ID back from self.drive.upload easily currently without mod.
                        # Assuming success means it worked.
                        session.add(doc)
                        await session.commit()
                        console_logger.info(f"[Drive] Uploaded: {action_log}")
                    else:
                        doc.gdrive_upload_status = UploadStatus.FAILED
                        session.add(doc)
                        await session.commit()
                        logging.error(f"Drive Upload Failed: {filepath}")

            except Exception as e:
                logging.error(f"Error processing {filepath}: {e}")
                if not self.dry_run:
                    await session.rollback()

async def main():
    parser = argparse.ArgumentParser(description='Migrate legacy markdown files to DB and Drive.')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without changes')
    args = parser.parse_args()

    migrator = Migrator(dry_run=args.dry_run)
    
    # 1. Find files
    files = glob.glob('data/**/*.md', recursive=True)
    console_logger.info(f"Found {len(files)} markdown files.")

    # 2. Process
    tasks = [migrator.process_file(f) for f in files]
    
    # Run with progress bar
    # Using gather might be too aggressive for Drive API rate limits.
    # Let's use a semaphore or sequential loop with tqdm.
    for f in tqdm(files, desc="Migrating"):
        await migrator.process_file(f)
        if not args.dry_run:
            await asyncio.sleep(0.5) # Rate limiting

if __name__ == "__main__":
    asyncio.run(main())
