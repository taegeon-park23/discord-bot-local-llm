
import requests
import json

BASE_URL = "http://localhost:8000"

def test_category_filtering():
    # 1. 모든 카테고리 목록 가져오기 (TagManager mappings 기반)
    # 실제로는 mappings을 읽어야 하지만, 여기서는 몇 가지 주요 카테고리로 테스트
    categories = ["Development", "AI & ML", "Design", "Uncategorized"]
    
    for cat in categories:
        print(f"\n--- Testing Category: {cat} ---")
        response = requests.get(f"{BASE_URL}/api/documents?category={cat}&limit=5")
        if response.status_code == 200:
            docs = response.json()
            print(f"Found {len(docs)} documents.")
            for doc in docs:
                # Backend API가 계산해서 보내주는 category 필드 확인
                print(f"  - [{doc.get('category')}] {doc.get('title')} (Tags: {doc.get('tags')})")
                
                # 검증: Uncategorized가 아닌 경우, 요청한 카테고리와 일치해야 함
                if cat != "Uncategorized":
                    if doc.get('category') != cat:
                        print(f"    [WARNING] Category mismatch! Expected {cat}, got {doc.get('category')}")
        else:
            print(f"Failed to fetch documents for category {cat}: {response.status_code}")

if __name__ == "__main__":
    try:
        test_category_filtering()
    except Exception as e:
        print(f"Error: {e}")
