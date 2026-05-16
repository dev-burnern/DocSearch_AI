# 포트폴리오 요약

## 프로젝트 개요

DocSearch AI는 사내 문서를 업로드하고 온프레미스 RAG로 검색과 질의응답을 제공하는 문서 검색 플랫폼입니다. V2는 V1 프로토타입을 유지한 상태에서 `develop` 브랜치에 FastAPI, React, PostgreSQL, Redis, Qdrant, MinIO, vLLM/OpenAI compatible endpoint 기반으로 재구축했습니다.

## 문제 정의

| 문제 | 해결 방향 |
| --- | --- |
| 사내 문서를 외부 SaaS로 보내기 어려움 | 로컬 또는 사내 GPU 환경에서 모델 서버를 직접 운영하는 온프레미스 구조 |
| 단순 검색만으로는 문서 근거 확인이 어려움 | chunk retrieval, rerank, citation 포함 채팅 응답 |
| RAG 답변 hallucination 위험 | relevance threshold, citation filtering, no-answer guard |
| 운영 장애 파악 어려움 | readiness, dependency health, 운영 이벤트, 관리자 운영 화면 |
| 포트폴리오 데모 환경 제약 | GPU 없는 노트북에서는 AI stub 기반 Notebook Compose로 기능 흐름 검증 |

## 역할과 기여

| 구분 | 내용 |
| --- | --- |
| 역할 | 백엔드, 프론트엔드, 인프라, RAG 파이프라인, 운영 문서 전반 구현 |
| 개발 방식 | 기능 단위 PR, 테스트 선행 또는 동반, `develop` 통합 |
| 주요 책임 | API Key 인증, 문서 처리, 인덱싱 큐, retrieval/rerank/chat, 감사 로그, 관리자 운영 화면, Docker Compose, 테스트/문서 |
| 품질 기준 | backend/frontend 자동 테스트, PR 단위 검증, 운영 영향 범위 명시 |

## 핵심 기능

| 영역 | 구현 내용 |
| --- | --- |
| 인증 | API Key 기반 workspace context, member/admin role 분리 |
| 문서 처리 | TXT/MD/PDF/DOCX parser, 빈 문서/깨진 파일/대용량 파일 오류 코드 |
| 저장소 | MinIO 원본 저장, PostgreSQL 문서 메타데이터/감사 로그, Qdrant vector store |
| 인덱싱 | in-process queue와 Redis queue, worker, 실패 사유 저장, retry, queue backlog 표시 |
| 검색 | Dense retrieval, workspace/document filter, hybrid search |
| RAG 채팅 | vLLM/OpenAI compatible gateway, BGE reranker, citation, no-answer guard |
| 운영 | `/health`, `/ready`, dependency health, rate limit, 운영 이벤트, 관리자 운영 화면 |
| 프론트엔드 | 문서 업로드/목록/검색/채팅/감사 로그/운영 상태 화면 |
| 로컬 검증 | Docker Compose, Notebook Compose, AI stub, 테스트/성능 기준표 |

## V1/V2 비교

| 항목 | V1 프로토타입 | V2 MVP |
| --- | --- | --- |
| 실행 구조 | 프로토타입 중심 | API, frontend, worker, gateway, storage 분리 |
| 인증 | 제한적 | API Key workspace/role 기반 |
| 문서 처리 | 기본 업로드 중심 | parser registry, 오류 코드, 재인덱싱, metadata |
| 검색 | 기본 retrieval | Qdrant dense + hybrid search |
| 답변 | 기본 RAG | rerank, citation filtering, no-answer guard |
| 운영 | 제한적 | readiness, dependency health, rate limit, 운영 이벤트 |
| 감사 | 제한적 | PostgreSQL 감사 로그, 필터, CSV export |
| 테스트 | 제한적 | backend/frontend 자동 테스트와 PR 검증 |

## 개발 히스토리

| 기간 | PR | 범위 | 결과 |
| --- | --- | --- | --- |
| 2026-05-12 | #1-#4 | V2 워크플로우, 스캐폴드, API Key 인증 | `develop` 기반 재구축 시작 |
| 2026-05-13 | #5-#11 | 문서 업로드, 인덱싱, Qdrant retrieval, LLM gateway, chat, audit | RAG backend 핵심 경계 완성 |
| 2026-05-14 | #13-#16 | PostgreSQL audit, 프론트 채팅/감사/문서 화면 | 사용자 흐름 UI 연결 |
| 2026-05-15 | #17-#26 | 문서 목록/삭제/재인덱싱, 감사 필터/export, 관리자 권한/운영 화면, rate limit | 운영 화면과 관리 기능 확장 |
| 2026-05-16 | #27-#31 | Redis rate limit, 운영 이벤트, 인덱싱 실패/재시도, 문서 처리 안정화 | 운영 하드닝과 문서 안정성 강화 |
| 2026-05-16 | #32-#39 | RAG grounding, vLLM retry, BGE-M3, hybrid search, citation/no-answer, 큐 visibility | RAG 품질과 운영 가시성 보강 |
| 2026-05-16 | #40 | 테스트/성능 기준과 포트폴리오 문서 | 데모와 리뷰 자료 정리 |

## 검증 현황

| 항목 | 기준 |
| --- | --- |
| Backend test | `.venv\Scripts\python.exe -m pytest backend\tests -q`, 140 passed |
| Frontend test | `npm.cmd run test`, 40 passed |
| Frontend build | `npm.cmd run build`, build passed |
| GitHub checks | PR별 `backend`, `frontend` checks 통과 |
| 로컬 노트북 | Notebook Compose로 AI stub 기반 기능 흐름 검증 가능 |

자세한 측정 절차는 [테스트 및 성능 기준표](test-performance-baseline.md)에 정리했습니다.

## 데모 시나리오

1. `docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml up --build`로 로컬 실행합니다.
2. `http://localhost:8080`에서 `local-dev-key`를 입력합니다.
3. TXT 또는 PDF 문서를 업로드합니다.
4. 문서 목록에서 인덱싱 상태와 chunk count를 확인합니다.
5. 검색 화면에서 업로드 문서의 키워드로 검색합니다.
6. 채팅 화면에서 문서 기반 질문을 하고 citation을 확인합니다.
7. 감사 로그 화면에서 질문/답변 기록을 확인합니다.
8. 운영 상태 화면에서 readiness, dependency, rate limit, indexing queue 상태를 확인합니다.

## 남은 개선점

| 우선순위 | 항목 | 이유 |
| --- | --- | --- |
| 높음 | README 최종 스크린샷 또는 데모 GIF | 포트폴리오 첫 인상 개선 |
| 높음 | 실제 vLLM/BGE 환경 성능표 작성 | stub이 아닌 모델 latency 근거 필요 |
| 중간 | OCR/스캔 PDF 처리 | 문서 타입 확장 |
| 중간 | semantic chunking | 긴 문서 검색 품질 개선 |
| 중간 | 운영 이벤트 영속화 또는 외부 알림 | 재시작 후 운영 이벤트 보존 |
| 낮음 | frontend code splitting | Vite chunk size 경고 완화 |

## 포트폴리오에서 강조할 점

- 단순 RAG demo가 아니라 인증, 저장소, 큐, 감사, 운영 상태까지 포함한 서비스 형태로 구현했습니다.
- GPU가 없는 노트북에서도 기능 흐름을 검증할 수 있게 Notebook Compose와 AI stub을 분리했습니다.
- 실제 운영 모델은 vLLM/OpenAI compatible endpoint로 교체 가능하게 만들었습니다.
- RAG 답변은 citation filtering과 no-answer guard로 근거 없는 답변을 줄이는 방향으로 설계했습니다.
- PR 단위로 기능을 나누고 각 PR에 검증 결과와 영향 범위를 남겼습니다.
