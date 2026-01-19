📄 제품 요구사항 정의서 (PRD)
프로젝트명: AI 지식 수집 및 분석 에이전트 (Knowledge Collector Bot)

버전: v2.0 (Deep Dive & Drive Integration)

작성일: 2026-01-19

1. 개요 (Overview)
1.1 배경
사용자가 습득하는 기술 블로그, 뉴스, 유튜브 영상 등 방대한 정보를 수동으로 정리하는 데 한계가 있음. 이를 자동화하여 **"수집 -> 요약 -> 심층 분석 -> 저장 -> 활용(RAG/Podcast)"**의 전 과정을 AI 에이전트에게 위임하고자 함.

1.2 목표
단순 링크 공유만으로 핵심 요약 및 태그가 포함된 마크다운 문서를 생성.

**Obsidian(로컬)**과 **Google Drive(클라우드)**에 이중 저장하여 지식 관리 및 NotebookLM 활용성 극대화.

로컬 LLM을 활용하여 비용 효율적이고 프라이빗한 데이터 처리 환경 구축.

2. 핵심 기능 (Key Features)
2.1 📥 지식 수집 및 요약 (Ingestion & Summarization)
트리거: 특정 채널(INPUT_CHANNEL_ID)에 URL이 포함된 메시지 게시.

지원 소스:

일반 웹: Playwright 및 Trafilatura를 활용한 동적 페이지 크롤링.

YouTube: yt-dlp를 활용한 자막(Transcript) 추출.

SNS: X(Twitter), Threads 등 동적 로딩 사이트 지원.

처리 로직:

콘텐츠 추출 후 로컬 LLM을 통해 JSON 포맷으로 분석 (제목, 3줄 요약, 카테고리, 태그).

결과를 Discord Embed로 즉시 회신.

2.2 🕵️‍♂️ 심층 분석 (Deep Dive Mode)
트리거: 링크가 있는 메시지에 탐정 이모지(🕵️‍♂️, 🔍 등) 반응 추가.

기능:

해당 콘텐츠를 재분석하여 심층 리포트 생성.

포함 내용: 핵심 논거, 기술적 상세 분석, 비판적 시각(장단점), 실무 적용 포인트.

출력: [DeepDive] 태그가 붙은 별도 마크다운 파일 생성 및 Discord 답장 전송.

2.3 💾 이중 저장소 동기화 (Dual Storage Sync)
Local (Obsidian):

Docker Volume을 통해 호스트의 옵시디언 볼트(Vault)에 .md 파일 자동 저장.

파일명 포맷: YYYY-MM-DD_제목.md

Cloud (Google Drive for NotebookLM):

Google Drive API를 사용하여 지정된 폴더(NotebookLM_Source)에 파일 자동 업로드.

목적: NotebookLM이 해당 폴더를 소스로 참조하여 Audio Overview(팟캐스트) 생성 가능하도록 함.

2.4 🧠 지식 활용 (Retrieval & Reporting)
Q&A (RAG):

명령어: !ask <질문>

기능: 저장된 로컬 마크다운 파일들을 검색하여 질문에 대한 답변 생성.

주간 리포트:

명령어: !weekly

기능: 최근 7일간 수집된 문서를 분석하여 주간 트렌드 및 학습 요약 리포트 생성 및 저장.

2.5 🌐 네트워크 및 접근성
외부 접속: ngrok을 통해 외부망(LTE 등)에서도 로컬 봇 및 옵시디언 뷰어 접속 가능.

주소 관리: !url 명령어로 변동되는 ngrok 주소를 즉시 확인.

3. 시스템 아키텍처 (System Architecture)
3.1 기술 스택
Language: Python 3.10+

Framework: Discord.py (Bot Interface)

Scraping: Playwright (Headless Browser), Trafilatura (Text Extraction), yt-dlp (YouTube)

AI Model: Local LLM (via LM Studio, OpenAI-compatible API)

Storage: Local Filesystem (Docker Volume), Google Drive API (PyDrive2)

Deployment: Docker Compose

3.2 데이터 흐름도 (Data Flow)
User -> Discord (Link)

Bot -> URL Parsing -> Content Extractor (Web/YouTube)

Bot -> Text Content -> Local LLM (Summarize/Deep Dive)

Bot -> Analysis Result -> Markdown Generator

Save System:

Path A: -> Local Volume (./data) -> Obsidian

Path B: -> Google Drive API -> NotebookLM Source Folder

Bot -> Discord (Embed Notification)

4. 파일 구조 및 포맷 (Data Structure)
4.1 마크다운 파일 포맷 (Frontmatter 포함)
Markdown

---
title: "기사의 제목"
date: 2026-01-19
category: "Tech/AI"
tags: ['LLM', 'Automation']
url: "https://original-link.com"
---
# 기사의 제목

## 📝 3줄 요약
- 요약 내용 1
- 요약 내용 2
- 요약 내용 3

## 🔗 원본 링크
https://original-link.com (Web)

(Deep Dive의 경우 하단에 상세 분석 내용 추가)
5. 향후 개선 계획 (Backlog)
벡터 데이터베이스 도입: 현재 단순 텍스트 매칭인 !ask 기능을 ChromaDB 등을 활용한 시멘틱 검색으로 고도화.

태그 표준화: LLM이 생성하는 태그를 기존 옵시디언 태그 목록과 대조하여 통일성 유지.

이미지 분석: 비전 모델(Vision Model)을 연동하여 이미지/스크린샷 내용도 분석에 포함.