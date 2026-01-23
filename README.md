# Discord Knowledge Bot (Local LLM & NotebookLM)

이 프로젝트는 디스코드 봇을 통해 기술 블로그, 유튜브 영상, 웹 문서를 자동으로 요약하고, 로컬 LLM을 사용하여 지식 베이스를 구축하는 시스템입니다. 수집된 문서는 주제별로 자동 분류되어 저장됩니다.

## 🚀 주요 기능

### 1. 콘텐츠 자동 요약 및 분류
- **링크 공유**: 디스코드 채널에 URL을 올리고 `👀` 이모지를 누르거나 봇이 자동으로 감지하면 요약을 시작합니다.
- **자동 분류**: 설정된 태그 매핑(`src/data/tag_mapping.yaml`)에 따라 문서를 적절한 폴더(`data/Development`, `data/AI & ML` 등)에 자동으로 저장합니다.
- **Deep Dive (심층 분석)**: 공유된 링크에 `🕵️‍♂️` (탐정) 이모지를 달면, LLM이 문서를 심층 분석하여 상세 리포트를 작성합니다.

### 2. 지식 검색 및 리포트
- **`!ask <질문>`**: 저장된 모든 문서(하위 폴더 포함)를 검색하여 질문에 대한 답변을 제공합니다.
- **`!weekly`**: 최근 7일간 저장된 문서를 바탕으로 주간 트렌드 리포트를 생성합니다.

---

## ⚙️ 설정 가이드

### 태그 매핑 및 폴더 분류 (`tag_mapping.yaml`)

이 봇은 `src/data/tag_mapping.yaml` 파일을 기준으로 문서를 분류합니다. LLM이 추출한 태그나 키워드가 이 설정 파일의 `synonyms`에 해당하면, 지정된 `topic` 폴더로 문서를 이동시킵니다.

#### 설정 파일 위치
`src/data/tag_mapping.yaml`

#### 작성 예시 (Example)

```yaml
version: 1.0
mappings:
  # 'Development' 폴더로 분류될 키워드들
  - topic: "Development"
    synonyms:
      - "python"
      - "javascript"
      - "typescript"
      - "web"
      - "backend"
      - "frontend"
      - "postgresql"  # postgres 관련 글은 Development 폴더로 감
      - "db"

  # 'AI & ML' 폴더로 분류될 키워드들
  - topic: "AI & ML"
    synonyms:
      - "ai"
      - "llm"
      - "machine learning"
      - "gpt"
      - "deep learning"
      - "rag"
      - "agent"

  # 'Design' 폴더로 분류될 키워드들
  - topic: "Design"
    synonyms:
      - "design"
      - "ui"
      - "ux"
      - "figma"

  # 매핑되지 않은 문서는 'Uncategorized' 폴더에 저장됩니다.
```

### 새로운 카테고리 추가 방법
1. `src/data/tag_mapping.yaml` 파일을 엽니다.
2. `mappings` 리스트 아래에 새로운 `topic`과 `synonyms`를 추가합니다.
3. 봇은 별도의 재시작 없이도 다음 요청부터(또는 `TagManager`가 다시 로드될 때) 변경된 설정을 반영합니다.

---

## 📂 폴더 구조

```
data/
├── Development/       # 개발 관련 문서
├── AI & ML/          # AI 관련 문서
├── Design/           # 디자인 관련 문서
├── Trends & News/    # 뉴스 및 트렌드
└── Uncategorized/    # 분류되지 않은 문서
```

## 🛠 실행 방법

```bash
# Docker Compose로 실행
docker-compose up -d --build
```
