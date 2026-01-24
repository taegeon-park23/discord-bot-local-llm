"""
Deep Dive End-to-End 통합 테스트
실제 DB 저장까지 테스트하는 스크립트
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.ai_handler import AIAgent
from src.services.db_service import DBService
from src.database.models import DocType
from src.logger import get_logger

logger = get_logger(__name__)

SAMPLE_DEEP_DIVE_CONTENT = """
# Python AsyncIO Best Practices

## 1. 🔍 핵심 논거 및 인사이트
AsyncIO는 단일 스레드에서 동시성을 달성하는 파이썬의 강력한 도구입니다.
I/O 바운드 작업에서 뛰어난 성능을 발휘합니다.

## 2. ⚙️ 기술적 심층 분석
- Event Loop 메커니즘
- Coroutine vs Future vs Task
- asyncio.gather()와 asyncio.create_task() 차이

## 3. ⚖️ 비판적 시각
멀티 코어 활용이 필요한 CPU 바운드 작업에는 부적합합니다.

## 4. 🚀 실무 적용 포인트
Discord Bot, Web Scraper, API Gateway 등에 최적화되어 있습니다.
"""

async def test_deep_dive_e2e():
    """Deep Dive의 전체 플로우를 테스트합니다 (태그 생성 + DB 저장)"""
    logger.info("=== Deep Dive E2E 테스트 시작 ===")
    
    # Step 1: AI Agent로 태그 생성
    ai_agent = AIAgent()
    logger.info("📝 Deep Dive 콘텐츠에서 태그 생성 중...")
    tags = ai_agent.generate_tags(SAMPLE_DEEP_DIVE_CONTENT)
    
    assert len(tags) > 0, "태그가 생성되지 않았습니다"
    logger.info(f"✅ 생성된 태그: {tags}")
    
    # Step 2: DB에 문서 등록 (태그 포함)
    test_filepath = "/tmp/test_deep_dive_e2e.md"
    logger.info("💾 DB에 문서 등록 중...")
    
    try:
        await DBService.register_document(
            title="[E2E Test] Deep Dive - Python AsyncIO",
            local_path=test_filepath,
            doc_type=DocType.DEEP_DIVE,
            source_url="https://example.com/asyncio-test",
            raw_tags=tags
        )
        logger.info("✅ DB 등록 성공")
    except Exception as e:
        logger.error(f"❌ DB 등록 실패: {e}", exc_info=True)
        return False
    
    # Step 3: DB에서 문서 조회 및 태그 검증
    logger.info("🔍 DB에서 문서 조회 중...")
    from src.database.engine import AsyncSessionLocal
    from src.database.models import Document
    from sqlalchemy.future import select
    
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.local_file_path == test_filepath)
            )
            doc = result.scalar_one_or_none()
            
            if not doc:
                logger.error("❌ 문서를 찾을 수 없습니다")
                return False
            
            logger.info(f"✅ 문서 조회 성공: {doc.title}")
            logger.info(f"   저장된 태그: {doc.tags}")
            
            # 검증
            assert doc.tags is not None, "태그가 None입니다"
            assert len(doc.tags) > 0, "태그 리스트가 비어있습니다"
            assert all(tag in tags for tag in doc.tags), "저장된 태그가 생성된 태그와 다릅니다"
            
            logger.info("✅ 태그 검증 성공!")
            
            # 정리: 테스트 데이터 삭제
            await db.delete(doc)
            await db.commit()
            logger.info("🧹 테스트 데이터 정리 완료")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ DB 조회 실패: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Deep Dive End-to-End 통합 테스트")
    print("="*60 + "\n")
    
    result = asyncio.run(test_deep_dive_e2e())
    
    print("\n" + "="*60)
    if result:
        print("🎉 E2E 테스트 성공!")
        print("Deep Dive 태그 생성 및 DB 저장이 정상적으로 작동합니다.")
        sys.exit(0)
    else:
        print("❌ E2E 테스트 실패")
        sys.exit(1)
