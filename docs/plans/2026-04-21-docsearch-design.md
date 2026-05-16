# DocSearch AI 설계 문서

- 작성일: 2026-04-21
- 상태: 설계 초안
- 대상 브랜치: `develop`
- 포지션: 백엔드 / AI 중심, 인프라 운영 역량 보조

## 1. 목표

DocSearch AI는 사내 문서를 안전하게 검색하고, 근거가 포함된 답변을 생성하는 온프레미스 RAG 시스템을 목표로 한다.

이번 재구축의 핵심은 다음 네 가지다.

- 문서 업로드부터 검색, 리랭킹, 답변 생성까지 이어지는 백엔드 설계
- 로컬 LLM 경계를 분리한 운영형 구조
- 비동기 문서 처리와 저장소 경계가 보이는 서비스 아키텍처
- 리뷰하기 쉬운 브랜치, PR, 커밋 흐름

## 2. 서비스 아키텍처

기준 서비스 구성은 아래와 같다.

- `frontend`: React + TypeScript + Vite
- `gateway`: Nginx API gateway
- `backend`: FastAPI API server
- `worker`: 비동기 인덱싱 워커
- `postgres`: 메타데이터 저장소
- `redis`: 캐시와 작업 큐
- `qdrant`: 벡터 데이터베이스
- `minio`: 원문 파일 저장소
- `llm`: 로컬 추론 서버

모든 구현은 `main`의 V1 프로토타입과 분리해서 `develop`에서 진행한다.

## 3. MVP 범위

포함:

- API Key 기반 인증
- 워크스페이스 범위 문서 접근
- PDF, TXT, Markdown 업로드
- 문서 저장, 청킹, 임베딩, 벡터 인덱싱
- Dense 검색 + 메타데이터 필터 + 리랭킹
- 로컬 LLM 기반 답변 생성
- 출처 포함 응답

후속:

- JWT 로그인과 RBAC
- DOCX, XLSX, PPTX, OCR
- 하이브리드 검색
- 모델 추천 UI
- 관리자 화면

## 4. 모델 선택

MVP 기본 모델 조합은 다음과 같다.

```text
LLM_MODEL=google/gemma-4-E4B-it
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

LLM 호출은 애플리케이션이 직접 추론 엔진에 붙지 않고, 게이트웨이 계층을 통해 수행한다.

## 5. 처리 흐름

```text
문서 업로드
-> 파일 저장
-> 처리 작업 생성
-> 파싱
-> 청킹
-> 임베딩
-> Qdrant 인덱싱
-> 사용자 질문 수신
-> 검색
-> 리랭킹
-> 컨텍스트 구성
-> 로컬 LLM 호출
-> 출처 포함 응답 반환
```

## 6. 브랜치 전략

```text
main
-> develop
   -> chore/workflow
   -> feat/scaffold
   -> feat/auth
   -> feat/ingestion
   -> feat/indexing-worker
   -> feat/retrieval
   -> feat/llm-gateway
   -> feat/chat-api
   -> feat/frontend-shell
```

## 7. 마일스톤

1. 스캐폴드와 런타임 경계
2. 인증과 요청 컨텍스트
3. 업로드와 저장소
4. 인덱싱 파이프라인
5. 검색과 리랭킹
6. 로컬 LLM 게이트웨이
7. 채팅 응답과 출처
8. 관측성과 하드닝
