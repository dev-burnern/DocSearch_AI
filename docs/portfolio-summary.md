# DocSearch AI 포트폴리오 요약

## 프로젝트 개요

DocSearch AI는 온프레미스 환경에서 문서를 업로드하고, 벡터 검색과 로컬 LLM을 이용해 문서 기반 질의응답을 제공하는 RAG 문서 검색 서비스입니다. 외부 SaaS API에 문서 본문을 보내지 않는 구성을 목표로 했고, FastAPI 백엔드, React 관리자 UI, Qdrant, MinIO, PostgreSQL, Redis, vLLM 호환 게이트웨이를 Docker Compose 기준으로 통합했습니다.

## 핵심 문제

- 사내 문서가 여러 형식으로 흩어져 있어 검색과 질의응답 흐름이 분리됩니다.
- 문서 본문과 질문이 외부 API로 나가면 보안 검토 부담이 큽니다.
- RAG 서비스는 검색, 인덱싱, LLM, 벡터 DB, 원본 저장소 중 하나만 실패해도 사용자가 원인을 파악하기 어렵습니다.
- 포트폴리오 관점에서는 기능 구현뿐 아니라 운영 상태, 감사 로그, 권한 경계, 테스트 기준까지 보여야 합니다.

## 해결 방향

- 문서 원본은 MinIO, 메타데이터와 감사 로그는 PostgreSQL, chunk vector는 Qdrant에 분리 저장했습니다.
- 업로드 이후 Redis 기반 인덱싱 큐를 통해 parsing, chunking, embedding, vector upsert를 비동기로 처리합니다.
- 검색은 dense retrieval과 hybrid search를 지원하고, 채팅은 reranker와 citation 검증을 거친 근거 기반 답변만 반환합니다.
- 사번 로그인과 역할 기반 접근 정책을 붙여 관리자와 일반 사용자의 문서 보안등급 접근 범위를 분리했습니다.
- `/ready`, 관리자 운영 화면, 운영 이벤트 저장소, 감사 로그 조회와 CSV 내보내기로 운영 확인 흐름을 갖췄습니다.

## 주요 기능

| 영역 | 구현 내용 |
| --- | --- |
| 인증/인가 | 사번/비밀번호 로그인, 회원가입, Bearer token, API Key 호환 인증, admin/member 역할 |
| 문서 처리 | PDF, TXT, DOCX, MD parsing, 빈 문서/깨진 파일/대용량 파일 예외 처리 |
| 문서 보안 | `general`, `internal`, `confidential`, `restricted` 보안등급, 역할 기반 접근 제한 |
| 인덱싱 | Redis 큐, 작업 상태, 실패 사유, 재시도, worker 분리 |
| 검색 | Qdrant dense retrieval, hybrid search, workspace/document/security filter |
| RAG 답변 | vLLM/OpenAI compatible gateway, BGE reranker 경계, citation 검증, 근거 부족 답변 차단 |
| 운영 | dependency health, rate limit backend 상태, 운영 이벤트, 관리자 운영 화면 |
| 감사 | 채팅 감사 로그 저장, 필터 조회, CSV export |
| UI | React/Ant Design 기반 채팅, 문서, 운영 상태, 감사 로그 화면 |

## 기술 스택

| 계층 | 기술 | 역할 |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, Ant Design | 관리자용 문서 검색 대시보드 |
| API | FastAPI, Pydantic | 인증, 문서, 검색, 채팅, 운영 API |
| Queue | Redis | 인덱싱 작업 큐, rate limit counter |
| Metadata | PostgreSQL | 문서 메타데이터, 사용자, 감사 로그 |
| Object Storage | MinIO | 원본 문서 저장 |
| Vector Store | Qdrant | chunk vector 저장과 유사도 검색 |
| Embedding | BGE-M3 compatible endpoint | chunk/query embedding 생성 |
| Reranker | BGE reranker compatible endpoint | 검색 근거 재정렬 |
| LLM | vLLM OpenAI compatible server | 문서 기반 답변 생성 |
| Infra | Docker Compose, Nginx | 로컬 온프레미스형 실행 구성 |

## 역할과 기여

| 구분 | 내용 |
| --- | --- |
| 역할 | 기획, 아키텍처 설계, 백엔드 API, 프론트엔드 UI, Docker Compose, 테스트, 문서화 |
| 개발 방식 | 기능을 PR 단위로 분리하고, 커밋을 인증/문서/검색/운영/프론트 영역별로 리뷰 가능하게 관리 |
| 검증 방식 | 백엔드 pytest, 프론트 Vitest, TypeScript build, GitHub Actions |
| 결과물 | 온프레미스 RAG MVP, 관리자 대시보드, 운영/감사 로그, 포트폴리오 문서 |

## 성과 요약

| 항목 | 결과 |
| --- | --- |
| 테스트 | 백엔드 160개 테스트 통과, 프론트 27개 테스트 통과 |
| 운영성 | readiness, dependency health, rate limit 상태, 운영 이벤트 저장 |
| 보안성 | 사번 로그인, role 기반 관리자 화면, 문서 보안등급 접근 정책 |
| RAG 품질 | hybrid search, reranker, citation 검증, 근거 부족 답변 차단 |
| 실행성 | Docker Compose 기준 API, worker, Redis, PostgreSQL, Qdrant, MinIO, gateway 통합 |

## 데모 시나리오

1. `2301029 / password`로 관리자 로그인
2. 문서 업로드 화면에서 보안등급을 선택해 문서 등록
3. 문서 목록에서 업로드 상태와 chunk 수 확인
4. 문서 검색에서 보안등급 필터와 검색 결과 확인
5. 채팅에서 문서 기반 답변과 citation 확인
6. 운영 상태 화면에서 backend, storage, vector store, LLM 상태 확인
7. 감사 로그 화면에서 질문 기록, 문서 ID, token 사용량, citation 확인

## 향후 보강

| 우선순위 | 항목 |
| --- | --- |
| 1 | 실제 BGE-M3 embedding과 reranker 서버 기준 latency 측정 |
| 2 | 문서별 샘플 데이터와 포트폴리오용 데모 스크립트 정리 |
| 3 | 운영 이벤트 알림을 관리자 화면에서 더 명확히 표시 |
| 4 | Docker Compose 기준 간단 부하 테스트 결과 추가 |
