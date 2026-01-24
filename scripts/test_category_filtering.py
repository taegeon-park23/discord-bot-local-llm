"""
Category 필터링 로직 테스트 스크립트

이 스크립트는 다음을 검증합니다:
1. TagManager.get_tags_for_category() 메서드 동작
2. 테스트 문서 생성 (tags 포함)
3. Category 필터링 API 호출
4. 예상 결과와 실제 결과 비교
"""

import sys
import os
import asyncio
import requests

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.tag_manager import TagManager
from src.database.engine import AsyncSessionLocal
from src.database.models import Document, DocType, UploadStatus
from sqlalchemy.future import select


async def test_tag_manager():
    """TagManager.get_tags_for_category() 메서드 테스트"""
    print("\n" + "="*60)
    print("TEST 1: TagManager.get_tags_for_category()")
    print("="*60)
    
    tm = TagManager()
    
    # Test 1: Valid category
    dev_tags = tm.get_tags_for_category("Development")
    print(f"✓ Development tags: {dev_tags[:5]}... (총 {len(dev_tags)}개)")
    assert len(dev_tags) > 0, "Development category should have tags"
    assert "python" in dev_tags, "Python should be in Development tags"
    
    # Test 2: Case insensitive
    dev_tags_lower = tm.get_tags_for_category("development")
    assert dev_tags == dev_tags_lower, "Category matching should be case-insensitive"
    print("✓ Case-insensitive matching works")
    
    # Test 3: Non-existent category
    invalid_tags = tm.get_tags_for_category("NonExistentCategory")
    assert invalid_tags == [], "Non-existent category should return empty list"
    print("✓ Non-existent category returns []")
    
    print("\n✅ TagManager tests passed!\n")


async def create_test_documents():
    """테스트용 문서 생성"""
    print("\n" + "="*60)
    print("TEST 2: Create Test Documents")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        # Check if test docs already exist
        result = await db.execute(
            select(Document).where(Document.title.like("TEST_%"))
        )
        existing = result.scalars().all()
        
        if existing:
            print(f"⚠ Found {len(existing)} existing test documents. Deleting...")
            for doc in existing:
                await db.delete(doc)
            await db.commit()
        
        # Create test documents
        test_docs = [
            {
                "title": "TEST_Python_Tutorial",
                "local_file_path": "/test/python_tutorial.md",
                "tags": ["python", "programming"],
                "doc_type": DocType.SUMMARY
            },
            {
                "title": "TEST_React_Guide",
                "local_file_path": "/test/react_guide.md",
                "tags": ["javascript", "react", "frontend"],
                "doc_type": DocType.SUMMARY
            },
            {
                "title": "TEST_Figma_Tips",
                "local_file_path": "/test/figma_tips.md",
                "tags": ["design", "ui", "figma"],
                "doc_type": DocType.SUMMARY
            },
            {
                "title": "TEST_AI_Research",
                "local_file_path": "/test/ai_research.md",
                "tags": ["ai", "llm", "research"],
                "doc_type": DocType.DEEP_DIVE
            }
        ]
        
        for doc_data in test_docs:
            doc = Document(
                title=doc_data["title"],
                local_file_path=doc_data["local_file_path"],
                tags=doc_data["tags"],
                doc_type=doc_data["doc_type"],
                gdrive_upload_status=UploadStatus.SUCCESS
            )
            db.add(doc)
            print(f"✓ Created: {doc.title} with tags {doc.tags}")
        
        await db.commit()
        print(f"\n✅ Created {len(test_docs)} test documents\n")


def test_api_category_filter():
    """API 엔드포인트 category 필터 테스트"""
    print("\n" + "="*60)
    print("TEST 3: API Category Filtering")
    print("="*60)
    
    base_url = "http://localhost:8000/api/documents"
    
    # Test 1: Filter by Development category
    print("\n[Test 3.1] Filter by 'Development':")
    response = requests.get(f"{base_url}?category=Development")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    print(f"  Found {len(data)} documents")
    dev_titles = [d['title'] for d in data if d['title'].startswith('TEST_')]
    print(f"  Test docs: {dev_titles}")
    
    # Should include Python_Tutorial and React_Guide
    assert any("Python" in t for t in dev_titles), "Should include Python tutorial"
    assert any("React" in t for t in dev_titles), "Should include React guide"
    assert not any("Figma" in t for t in dev_titles), "Should NOT include Figma tips"
    print("  ✓ Correct documents returned")
    
    # Test 2: Filter by Design category
    print("\n[Test 3.2] Filter by 'Design':")
    response = requests.get(f"{base_url}?category=Design")
    assert response.status_code == 200
    data = response.json()
    
    print(f"  Found {len(data)} documents")
    design_titles = [d['title'] for d in data if d['title'].startswith('TEST_')]
    print(f"  Test docs: {design_titles}")
    
    assert any("Figma" in t for t in design_titles), "Should include Figma tips"
    assert not any("Python" in t for t in design_titles), "Should NOT include Python"
    print("  ✓ Correct documents returned")
    
    # Test 3: Filter by AI & ML category
    print("\n[Test 3.3] Filter by 'AI & ML':")
    response = requests.get(f"{base_url}?category=AI%20%26%20ML")
    assert response.status_code == 200
    data = response.json()
    
    print(f"  Found {len(data)} documents")
    ai_titles = [d['title'] for d in data if d['title'].startswith('TEST_')]
    print(f"  Test docs: {ai_titles}")
    
    assert any("AI_Research" in t for t in ai_titles), "Should include AI Research"
    print("  ✓ Correct documents returned")
    
    # Test 4: Invalid category
    print("\n[Test 3.4] Filter by invalid category:")
    response = requests.get(f"{base_url}?category=InvalidCategory")
    assert response.status_code == 200
    data = response.json()
    test_docs_count = len([d for d in data if d['title'].startswith('TEST_')])
    print(f"  Found {test_docs_count} test documents (should be 0)")
    assert test_docs_count == 0, "Invalid category should return no test docs"
    print("  ✓ Returns empty result")
    
    # Test 5: No filter (all documents)
    print("\n[Test 3.5] No filter (all documents):")
    response = requests.get(base_url)
    assert response.status_code == 200
    data = response.json()
    all_test_docs = [d for d in data if d['title'].startswith('TEST_')]
    print(f"  Found {len(all_test_docs)} test documents (should be 4)")
    assert len(all_test_docs) == 4, "Should return all test documents"
    print("  ✓ All documents returned")
    
    print("\n✅ All API tests passed!\n")


async def main():
    """메인 테스트 실행"""
    print("\n" + "🚀 "*30)
    print("Category-Based Filtering System Test")
    print("🚀 "*30)
    
    try:
        # Test 1: TagManager
        await test_tag_manager()
        
        # Test 2: Create test documents
        await create_test_documents()
        
        # Test 3: API filtering
        test_api_category_filter()
        
        print("\n" + "✅ "*30)
        print("ALL TESTS PASSED!")
        print("✅ "*30 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
