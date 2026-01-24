"""
레거시 문서의 tags 필드를 채우는 마이그레이션 스크립트

Usage:
    # Dry run (미리보기)
    python scripts/migrate_legacy_tags.py --dry-run
    
    # 실제 실행
    python scripts/migrate_legacy_tags.py
"""

import asyncio
import argparse
import re
from pathlib import Path
from typing import List, Set

from src.database.engine import AsyncSessionLocal
from src.database.models import Document
from src.services.tag_manager import TagManager
from sqlalchemy.future import select
from src.logger import get_logger

logger = get_logger(__name__)

# 폴더명 -> Topic 매핑 (수동 정의)
FOLDER_TO_TOPIC = {
    "AI & ML": "AI & ML",
    "AI Agent": "AI & ML",
    "Design": "Design",
    "Development": "Development",
    "DevOps & Cloud": "DevOps & Cloud",
    "Data Science": "Data Science",
    "Security": "Security",
    "API": "Development",
    "B-tree": "Development",
    "Custom Hooks": "Development",
    # 매핑 제외
    "Misc": None,
    "Uncategorized": None,
    "베스팅": None,
    ".obsidian": None,
    ".trash": None,
}


async def delete_test_documents(dry_run: bool = False):
    """TEST_로 시작하는 테스트 문서 삭제"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.title.like("TEST_%"))
        )
        test_docs = result.scalars().all()
        
        if not test_docs:
            logger.info("No test documents found to delete.")
            return 0
        
        logger.info(f"Found {len(test_docs)} test documents to delete:")
        for doc in test_docs:
            logger.info(f"  - {doc.id}: {doc.title}")
        
        if not dry_run:
            for doc in test_docs:
                await db.delete(doc)
            await db.commit()
            logger.info(f"✓ Deleted {len(test_docs)} test documents")
        else:
            logger.info(f"[DRY RUN] Would delete {len(test_docs)} test documents")
        
        return len(test_docs)


def infer_tags_from_path(local_path: str) -> Set[str]:
    """경로에서 폴더명을 추출하여 tags 추론"""
    tags = set()
    
    # /app/data/{FOLDER}/ 패턴에서 폴더명 추출
    # 예: "/app/data/AI & ML/some_file.md" -> "AI & ML"
    try:
        path_obj = Path(local_path)
        parts = path_obj.parts
        
        # /app/data 다음에 오는 폴더명 찾기
        if len(parts) > 3 and parts[1] == "app" and parts[2] == "data":
            folder_name = parts[3]
            
            # 매핑 확인
            topic = FOLDER_TO_TOPIC.get(folder_name)
            if topic:
                # TagManager를 통해 해당 Topic의 대표 태그 가져오기
                tm = TagManager()
                topic_tags = tm.get_tags_for_category(topic)
                if topic_tags:
                    # 대표 태그 몇 개만 추가 (너무 많으면 overwhelming)
                    tags.update(topic_tags[:3])
    except Exception as e:
        logger.debug(f"Failed to infer tags from path {local_path}: {e}")
    
    return tags


def infer_tags_from_title(title: str, tag_manager: TagManager) -> Set[str]:
    """Title에서 키워드를 찾아 tags 추론 (단어 경계 사용)"""
    tags = set()
    title_lower = title.lower()
    
    for group in tag_manager.mappings:
        synonyms = group.get('synonyms', [])
        
        for synonym in synonyms:
            # 단어 경계를 사용하여 정확한 매칭
            # 예: 'js'는 'javascript'에서 매칭 안 됨
            pattern = r'\b' + re.escape(synonym.lower()) + r'\b'
            if re.search(pattern, title_lower):
                tags.add(synonym.lower())
    
    return tags


async def migrate_tags(dry_run: bool = False, force: bool = False):
    """레거시 문서의 tags 필드 채우기"""
    tm = TagManager()
    
    async with AsyncSessionLocal() as db:
        # 빈 tags를 가진 문서만 조회 (force가 아니면)
        if force:
            result = await db.execute(select(Document))
        else:
            result = await db.execute(
                select(Document).where(Document.tags == [])
            )
        
        documents = result.scalars().all()
        
        if not documents:
            logger.info("No documents to migrate.")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Found {len(documents)} documents to process")
        logger.info(f"{'='*60}\n")
        
        updated_count = 0
        
        for doc in documents:
            # 경로 기반 추론
            path_tags = infer_tags_from_path(doc.local_file_path)
            
            # 제목 기반 추론
            title_tags = infer_tags_from_title(doc.title, tm)
            
            # 합치기
            combined_tags = path_tags | title_tags
            
            if combined_tags:
                # 정규화된 형태로 변환
                normalized_tags = tm.normalize_tags(list(combined_tags))
                
                logger.info(f"[{doc.id}] {doc.title[:50]}")
                logger.info(f"  Path: {doc.local_file_path[:60]}")
                logger.info(f"  Inferred Tags: {sorted(normalized_tags)}")
                
                if not dry_run:
                    doc.tags = normalized_tags
                    updated_count += 1
                else:
                    logger.info(f"  [DRY RUN] Would update tags")
                
                logger.info("")
        
        if not dry_run:
            await db.commit()
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Migration complete: Updated {updated_count} documents")
            logger.info(f"{'='*60}")
        else:
            logger.info(f"\n{'='*60}")
            logger.info(f"[DRY RUN] Would update {updated_count} documents")
            logger.info(f"{'='*60}")


async def main():
    parser = argparse.ArgumentParser(description="Migrate legacy document tags")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--force", action="store_true", help="Process all documents, not just empty tags")
    args = parser.parse_args()
    
    logger.info("\n" + "🚀 " * 30)
    logger.info("Legacy Tags Migration Script")
    logger.info("🚀 " * 30 + "\n")
    
    if args.dry_run:
        logger.info("⚠️  DRY RUN MODE - No changes will be saved\n")
    
    # Step 1: Delete test documents
    logger.info("Step 1: Cleaning up test documents...")
    deleted = await delete_test_documents(dry_run=args.dry_run)
    
    # Step 2: Migrate tags
    logger.info("\nStep 2: Migrating tags for legacy documents...")
    await migrate_tags(dry_run=args.dry_run, force=args.force)
    
    logger.info("\n✅ Script completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(main())
