# DocSearch AI

DocSearch AI는 사내 문서를 업로드하고, 로컬 vLLM 기반 RAG로 검색과 질의응답을 제공하는 온프레미스 문서 검색 플랫폼입니다. 문서 원본, 메타데이터, 벡터 인덱스, LLM 추론 경계를 모두 사내망 또는 로컬 실행 환경에 둘 수 있도록 구성했습니다.

`main` 브랜치는 기존 V1 프로토타입을 유지하고, `develop` 브랜치는 새 서비스 아키텍처를 기준으로 재구축을 진행합니다.

현재 기준 서비스 구성은 다음과 같습니다.

- `frontend`: React + TypeScript + Vite + Ant Design 웹 UI
- `gateway`: Nginx 리버스 프록시
- `backend`: FastAPI API 서버
- `worker`: 비동기 인덱싱 워커 경계
- `postgres`: 메타데이터 저장소
- `redis`: 캐시 및 작업 큐
- `qdrant`: 벡터 데이터베이스
- `minio`: 원본 문서 저장소
- `vLLM`: 로컬 추론 엔드포인트
- `reranker`: BGE 호환 리랭커 엔드포인트

## 저장소 구조

```text
backend/             FastAPI 서비스
frontend/            React 웹 애플리케이션
infra/compose/       Docker Compose 실행 구성
infra/nginx/         게이트웨이 설정
docs/                포트폴리오, 아키텍처, 운영 문서
```

## 포트폴리오 문서

- [포트폴리오 요약](docs/portfolio-summary.md)
- [아키텍처](docs/architecture.md)
- [Agent Flow](docs/agent-flow.md)
- [테스트와 성능 기준](docs/test-performance-baseline.md)
- [PR 단위 개발 히스토리](docs/pr-history.md)
- [LLM 운영 가이드](docs/llm-operations.md)
- [노트북 로컬 테스트 가이드](docs/notebook-local-test.md)
- [개발 워크플로우](docs/development-workflow.md)

## 빠른 실행

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

로컬 기본 주소:

- 앱 게이트웨이: `http://localhost:8080`
- 백엔드 문서: `http://localhost:8000/docs`
- 프론트엔드 개발 서버: `http://localhost:5173`
- MinIO 콘솔: `http://localhost:9001`
- vLLM 엔드포인트: `http://localhost:8100`

## 로컬 로그인과 인증

프론트엔드는 사번과 비밀번호 기반 로그인을 사용합니다. 로컬 기본 계정은 다음과 같습니다.

| 사번 | 비밀번호 | 역할 | 용도 |
| --- | --- | --- | --- |
| `2301029` | `password` | `admin` | 관리자 화면, 감사 로그, 전체 보안등급 문서 확인 |
| `1001` | `password` | `admin` | 보조 관리자 계정 |
| `1002` | `password` | `member` | 일반 사용자 권한 확인 |

API 클라이언트 호환을 위해 `DOCSEARCH_API_KEYS`도 유지합니다. 형식은 `api_key|workspace_id|workspace_name(|role)`이며, `role`은 `member` 또는 `admin`입니다. 역할을 생략하면 `member`로 처리됩니다. 로컬 Compose 기본값은 관리자 검토용 `local-dev-key`와 일반 사용자 확인용 `local-member-key`를 같은 워크스페이스에 등록합니다.

문서 보안등급은 `general`, `internal`, `confidential`, `restricted`를 지원합니다. `admin`은 모든 등급을 접근할 수 있고, `member`는 `general`, `internal`만 업로드, 목록 조회, 검색, 채팅, 삭제, 재인덱싱에서 접근할 수 있습니다.

## 운영 상태 점검

`/health`는 프로세스 생존 여부를 빠르게 반환하고, `/ready`는 운영 준비 상태를 반환합니다. `DEPENDENCY_HEALTH_CHECKS_ENABLED=true`이면 `/ready`에 PostgreSQL, Qdrant, MinIO, vLLM 연결 상태가 포함됩니다. Redis 큐, Redis rate limit, BGE Reranker는 해당 백엔드가 활성화된 경우에만 점검합니다.

개발 환경에서는 외부 점검이 기본 비활성화이고, 운영 환경에서는 기본 활성화됩니다. `DEPENDENCY_HEALTH_TIMEOUT_SECONDS`로 각 의존성 점검 타임아웃을 조정할 수 있습니다.

## 운영 요청 제한

`/v1/*` API는 API Key가 있으면 API Key 기준, 없으면 클라이언트 IP 기준으로 rate limit을 적용할 수 있습니다. 제한 초과 시 HTTP 429와 `Retry-After` 헤더를 반환합니다. `/health`, `/ready`, `/docs`, `/openapi.json` 같은 운영 점검과 문서 경로는 제한 대상에서 제외됩니다.

개발 환경에서는 기본 비활성화이고, 운영 환경에서는 기본 활성화됩니다. `RATE_LIMIT_ENABLED`, `RATE_LIMIT_BACKEND`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`로 활성화 여부, 저장소, 제한량을 조정할 수 있습니다. `RATE_LIMIT_BACKEND=memory`는 단일 API 컨테이너용 인메모리 제한이고, `RATE_LIMIT_BACKEND=redis`는 여러 API 인스턴스가 같은 카운터를 공유하는 분산 제한입니다. Redis key에는 API Key 원문을 저장하지 않고 SHA-256 해시를 사용합니다. Redis 장애 시 기본값은 `RATE_LIMIT_FAIL_OPEN=true`라서 요청을 통과시키고 운영 화면에 backend 상태를 드러냅니다.

## 관리자 운영 상태

관리자 역할 계정 또는 API Key로 운영 상태 화면에 접근할 수 있습니다. 운영 상태 화면은 `/v1/admin/operations`를 통해 readiness 결과, 외부 의존성 점검 목록, rate limit과 백엔드 설정 요약을 표시합니다. API Key, DB URL, MinIO Secret, LLM API Key 같은 민감 설정은 응답에 포함하지 않습니다.

## 현재 범위

현재 기준선에는 서비스 경계, 사번 로그인과 회원가입, Bearer token 인증, API Key 호환 인증, 역할 기반 관리자 화면, 문서 보안등급 접근 정책, 상태 확인 엔드포인트, 운영 준비 상태 진단, 외부 의존성 상태 점검, 기본 보안 응답 헤더, Redis 기반 분산 rate limit, 관리자 운영 상태 API와 화면, 로컬 실행 설정, CI, 문서 업로드, 문서 메타데이터 저장소와 목록 조회 API, 문서 삭제/재인덱싱 API, Redis 기반 인덱싱 큐와 재시도 정책, 청킹과 임베딩 파이프라인, Qdrant 기반 Dense retrieval, hybrid search, 워크스페이스/문서/보안등급 필터, BGE-M3 embedding 경계, BGE reranker 경계, vLLM/OpenAI 호환 LLM 게이트웨이, 근거 부족 답변 차단, citation 포함 채팅 API, PostgreSQL 감사 로그 저장소, 관리자 전용 감사 로그 조회 필터와 CSV 내보내기, 프론트엔드 채팅/문서/운영/감사 로그 화면이 포함되어 있습니다.
