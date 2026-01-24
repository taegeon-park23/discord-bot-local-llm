"""
Tag Analytics 배치 작업을 수동으로 트리거하고 결과를 검증하는 스크립트
"""
import asyncio
from src.services.tag_analytics import TagAnalyticsService
from src.database.engine import AsyncSessionLocal
from sqlalchemy import select, func
from src.database.models import TagStatistics, BatchJobState

async def main():
    print("=" * 60)
    print("🚀 Triggering Tag Analytics Batch Job...")
    print("=" * 60)
    
    # 배치 작업 실행
    await TagAnalyticsService.run_analytics()
    
    print("\n" + "=" * 60)
    print("📊 Verification Results")
    print("=" * 60)
    
    # 결과 검증
    async with AsyncSessionLocal() as db:
        # 1. BatchJobState 확인
        job_state = await db.execute(
            select(BatchJobState).where(BatchJobState.job_name == "tag_analytics")
        )
        state = job_state.scalar_one_or_none()
        
        if state:
            print(f"\n✅ Batch Job State:")
            print(f"   - Job Name: {state.job_name}")
            print(f"   - Last Processed ID: {state.last_processed_id}")
            print(f"   - Last Run At: {state.last_run_at}")
        else:
            print("\n❌ No batch job state found!")
        
        # 2. TagStatistics 상위 20개 조회
        top_tags = await db.execute(
            select(TagStatistics.tag, TagStatistics.count)
            .order_by(TagStatistics.count.desc())
            .limit(20)
        )
        tags = top_tags.all()
        
        print(f"\n✅ Top 20 Tags by Count:")
        print(f"   {'Rank':<6}{'Tag':<30}{'Count':<10}")
        print("   " + "-" * 46)
        for idx, (tag, count) in enumerate(tags, 1):
            print(f"   {idx:<6}{tag:<30}{count:<10}")
        
        # 3. 전체 통계
        total_tags = await db.execute(select(func.count(TagStatistics.id)))
        total = total_tags.scalar()
        
        total_count = await db.execute(select(func.sum(TagStatistics.count)))
        total_doc_tags = total_count.scalar() or 0
        
        print(f"\n✅ Overall Statistics:")
        print(f"   - Total Unique Tags: {total}")
        print(f"   - Total Tag Occurrences: {total_doc_tags}")
        
    print("\n" + "=" * 60)
    print("✨ Verification Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
