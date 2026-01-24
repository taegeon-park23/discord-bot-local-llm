"""
동시성 Race Condition 테스트 스크립트

Summary와 DeepDive 작업을 동시에 실행했을 때:
1. DeepDive의 DB 상태가 PENDING이 아닌 SUCCESS가 되는지 확인
2. DeepDive의 title이 "DeepDive"가 아닌 적절한 제목인지 확인
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.db_service import DBService
from src.database.models import DocType, UploadStatus
from sqlalchemy.future import select
from src.database.engine import AsyncSessionLocal
from src.database.models import Document

async def simulate_concurrent_tasks():
    """Summary와 DeepDive를 거의 동시에 실행하여 DB 경쟁 상태를 시뮬레이션"""
    
    test_url = "https://example.com/test-article"
    test_title_summary = "테스트 기사 제목"
    test_title_deepdive = "DeepDive - 테스트 기사 제목"
    
    # 테스트 전 기존 데이터 정리
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.source_url == test_url)
        )
        existing = result.scalars().all()
        for doc in existing:
            await db.delete(doc)
        await db.commit()
    
    print("🧪 Starting concurrent task simulation...")
    
    # Summary와 DeepDive를 동시에 실행
    tasks = [
        DBService.register_document(
            title=test_title_summary,
            local_path=f"/tmp/summary_{test_url.replace('/', '_')}.md",
            doc_type=DocType.SUMMARY,
            source_url=test_url
        ),
        DBService.register_document(
            title=test_title_deepdive,
            local_path=f"/tmp/deepdive_{test_url.replace('/', '_')}.md",
            doc_type=DocType.DEEP_DIVE,
            source_url=test_url
        )
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 결과 확인
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Task {i+1} failed: {result}")
        else:
            print(f"✅ Task {i+1} registered: {result}")
    
    # Status Update도 동시에 테스트
    print("\n🧪 Testing concurrent status updates...")
    
    status_tasks = [
        DBService.update_upload_status(
            local_path=f"/tmp/summary_{test_url.replace('/', '_')}.md",
            status=UploadStatus.SUCCESS
        ),
        DBService.update_upload_status(
            local_path=f"/tmp/deepdive_{test_url.replace('/', '_')}.md",
            status=UploadStatus.SUCCESS
        )
    ]
    
    await asyncio.gather(*status_tasks, return_exceptions=True)
    
    # 최종 DB 상태 확인
    print("\n📊 Final DB state:")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.source_url == test_url)
        )
        docs = result.scalars().all()
        
        for doc in docs:
            print(f"  - {doc.doc_type.value}: '{doc.title}' | Status: {doc.gdrive_upload_status.value}")
            
            # Validation
            if doc.doc_type == DocType.DEEP_DIVE:
                assert doc.gdrive_upload_status == UploadStatus.SUCCESS, "DeepDive status should be SUCCESS"
                assert doc.title != "DeepDive", "DeepDive title should not be generic"
                print(f"    ✅ DeepDive validation passed")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(simulate_concurrent_tasks())
