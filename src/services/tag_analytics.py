from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.database.models import Document, TagStatistics, BatchJobState
from src.database.engine import AsyncSessionLocal
from src.logger import get_logger
from datetime import datetime
from typing import Dict
import asyncio

logger = get_logger(__name__)

class TagAnalyticsService:
    """태그 통계를 계산하고 관리하는 서비스"""
    
    BATCH_SIZE = 1000  # 한 번에 처리할 문서 수
    JOB_NAME = "tag_analytics"
    
    @staticmethod
    async def run_analytics():
        """
        배치 작업: 새로운 문서들의 태그를 집계하여 TagStatistics 업데이트
        증분 업데이트 방식으로 last_processed_id 이후의 문서만 처리
        """
        logger.info("[TagAnalytics] Starting tag analytics batch job...")
        
        async with AsyncSessionLocal() as db:
            try:
                # 1. 마지막 처리된 ID 가져오기
                last_id = await TagAnalyticsService._get_last_processed_id(db)
                logger.info(f"[TagAnalytics] Last processed ID: {last_id}")
                
                # 2. 새로운 문서들 처리
                total_processed = 0
                tag_counts: Dict[str, int] = {}
                
                while True:
                    # 문서를 배치 단위로 가져오기
                    query = select(Document).where(Document.id > last_id).order_by(Document.id).limit(TagAnalyticsService.BATCH_SIZE)
                    result = await db.execute(query)
                    documents = result.scalars().all()
                    
                    if not documents:
                        break
                    
                    # 각 문서의 태그 집계
                    for doc in documents:
                        if doc.tags:
                            for tag in doc.tags:
                                # 태그 정규화 (소문자)
                                normalized_tag = tag.lower().strip()
                                if normalized_tag:
                                    tag_counts[normalized_tag] = tag_counts.get(normalized_tag, 0) + 1
                    
                    # 처리된 문서 수 누적
                    total_processed += len(documents)
                    last_id = documents[-1].id
                    
                    logger.info(f"[TagAnalytics] Processed {total_processed} documents so far...")
                
                # 3. TagStatistics 테이블 업데이트 (UPSERT)
                if tag_counts:
                    await TagAnalyticsService._upsert_tag_statistics(db, tag_counts)
                    logger.info(f"[TagAnalytics] Updated {len(tag_counts)} unique tags")
                
                # 4. BatchJobState 업데이트
                await TagAnalyticsService._update_job_state(db, last_id)
                
                await db.commit()
                logger.info(f"[TagAnalytics] ✅ Batch job completed. Processed {total_processed} new documents.")
                
            except Exception as e:
                logger.error(f"[TagAnalytics] ❌ Error during analytics: {e}")
                await db.rollback()
                raise
    
    @staticmethod
    async def _get_last_processed_id(db: AsyncSession) -> int:
        """마지막으로 처리된 문서 ID 조회"""
        result = await db.execute(
            select(BatchJobState.last_processed_id).where(BatchJobState.job_name == TagAnalyticsService.JOB_NAME)
        )
        last_id = result.scalar_one_or_none()
        return last_id if last_id is not None else 0
    
    @staticmethod
    async def _upsert_tag_statistics(db: AsyncSession, tag_counts: Dict[str, int]):
        """
        TagStatistics 테이블에 UPSERT (PostgreSQL)
        기존 태그가 있으면 count를 증가, 없으면 새로 생성
        """
        for tag, count in tag_counts.items():
            stmt = pg_insert(TagStatistics).values(
                tag=tag,
                count=count,
                last_updated=datetime.now()
            )
            # ON CONFLICT: tag가 이미 존재하면 count 증가
            stmt = stmt.on_conflict_do_update(
                index_elements=['tag'],
                set_={
                    'count': TagStatistics.count + stmt.excluded.count,
                    'last_updated': datetime.now()
                }
            )
            await db.execute(stmt)
    
    @staticmethod
    async def _update_job_state(db: AsyncSession, last_id: int):
        """BatchJobState 업데이트 또는 생성"""
        stmt = pg_insert(BatchJobState).values(
            job_name=TagAnalyticsService.JOB_NAME,
            last_processed_id=last_id,
            last_run_at=datetime.now()
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['job_name'],
            set_={
                'last_processed_id': last_id,
                'last_run_at': datetime.now()
            }
        )
        await db.execute(stmt)
    
    @staticmethod
    async def get_top_tags(db: AsyncSession, limit: int = 100, offset: int = 0):
        """
        상위 태그 목록 조회 (count 내림차순)
        """
        query = select(TagStatistics.tag, TagStatistics.count).order_by(
            TagStatistics.count.desc(),
            TagStatistics.tag  # 동일 count일 때 태그명으로 정렬
        ).offset(offset).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [{"tag": row.tag, "count": row.count} for row in rows]
