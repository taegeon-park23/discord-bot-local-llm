"""
Deep Dive 태그 생성 기능 테스트 스크립트

이 스크립트는 AIAgent.generate_tags 메서드가 올바르게 작동하는지 검증합니다.
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.ai_handler import AIAgent
from src.logger import get_logger

logger = get_logger(__name__)

# 테스트용 샘플 텍스트 (기술 문서 예시)
SAMPLE_TEXT = """
# Python AsyncIO와 Discord Bot 개발

## Introduction
AsyncIO는 Python 3.4부터 도입된 비동기 프로그래밍 라이브러리입니다.
이를 활용하면 Discord Bot과 같은 I/O 바운드 애플리케이션을 효율적으로 개발할 수 있습니다.

## Key Concepts
- Event Loop: 비동기 작업을 스케줄링하는 핵심 컴포넌트
- Coroutines: async def로 정의되는 비동기 함수
- Tasks: 이벤트 루프에서 실행되는 코루틴 래퍼

## Discord Bot with AsyncIO
Discord.py 라이브러리는 AsyncIO 기반으로 설계되어 있어, 
대규모 서버에서도 높은 퍼포먼스를 발휘할 수 있습니다.

## Best Practices
1. 블로킹 I/O를 asyncio.to_thread로 처리
2. 적절한 에러 핸들링
3. Graceful Shutdown 구현
"""

def test_generate_tags():
    """AIAgent.generate_tags 메서드를 테스트합니다."""
    logger.info("=== Deep Dive 태그 생성 테스트 시작 ===")
    
    # AIAgent 인스턴스 생성
    try:
        ai_agent = AIAgent()
        logger.info("✅ AIAgent 초기화 성공")
    except Exception as e:
        logger.error(f"❌ AIAgent 초기화 실패: {e}")
        return False
    
    # 태그 생성 테스트
    try:
        logger.info("📝 샘플 텍스트로 태그 생성 시도...")
        tags = ai_agent.generate_tags(SAMPLE_TEXT)
        
        # 검증
        assert isinstance(tags, list), f"태그는 리스트여야 하지만 {type(tags)}가 반환됨"
        assert len(tags) > 0, "태그 리스트가 비어있습니다"
        assert all(isinstance(tag, str) for tag in tags), "모든 태그는 문자열이어야 합니다"
        
        logger.info(f"✅ 태그 생성 성공!")
        logger.info(f"   생성된 태그 ({len(tags)}개): {tags}")
        
        # 예상되는 태그 포함 여부 확인 (선택적)
        expected_keywords = ['python', 'asyncio', 'discord', 'bot']
        tags_lower = [t.lower() for t in tags]
        found_keywords = [k for k in expected_keywords if any(k in tag for tag in tags_lower)]
        
        if found_keywords:
            logger.info(f"   예상 키워드 발견: {found_keywords}")
        
        return True
        
    except AssertionError as e:
        logger.error(f"❌ 검증 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 태그 생성 중 오류: {e}", exc_info=True)
        return False


def test_empty_text():
    """빈 텍스트 입력 시 빈 리스트 반환 테스트"""
    logger.info("\n=== 빈 텍스트 처리 테스트 ===")
    
    ai_agent = AIAgent()
    
    # 짧은 텍스트
    short_text = "Hello"
    result = ai_agent.generate_tags(short_text)
    assert result == [], f"짧은 텍스트는 빈 리스트를 반환해야 하지만 {result}가 반환됨"
    logger.info("✅ 짧은 텍스트 처리 정상")
    
    # None 입력
    result = ai_agent.generate_tags(None)
    assert result == [], f"None은 빈 리스트를 반환해야 하지만 {result}가 반환됨"
    logger.info("✅ None 입력 처리 정상")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Deep Dive 태그 생성 기능 테스트")
    print("="*60 + "\n")
    
    test_results = []
    
    # Test 1: 정상 태그 생성
    test_results.append(("정상 태그 생성", test_generate_tags()))
    
    # Test 2: 엣지 케이스
    test_results.append(("빈 텍스트 처리", test_empty_text()))
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_pass = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n총 {total_pass}/{total_tests} 테스트 통과")
    
    if total_pass == total_tests:
        print("🎉 모든 테스트 성공!")
        sys.exit(0)
    else:
        print("⚠️ 일부 테스트 실패")
        sys.exit(1)
