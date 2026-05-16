# 테스트와 성능 기준

## 검증 기준

이 문서는 DocSearch AI V2 MVP의 포트폴리오 제출 기준 테스트와 성능 측정 항목을 정리합니다. 현재 저장소에는 자동화 테스트와 CI 기준이 준비되어 있고, 실제 latency 수치는 실행 환경마다 달라지므로 로컬 Docker Compose 환경에서 별도 측정해 채우는 방식으로 관리합니다.

## 자동화 테스트 현황

| 영역 | 명령 | 현재 기준 |
| --- | --- | --- |
| Backend | `.venv\Scripts\python.exe -m pytest backend\tests` | 160 passed |
| Frontend unit | `npm.cmd test` | 27 passed |
| Frontend build | `npm.cmd run build` | 통과, Vite chunk size warning 있음 |
| CI backend | GitHub Actions `backend` job | pass |
| CI frontend | GitHub Actions `frontend` job | pass |

마지막 로컬 확인 기준:

- 백엔드: 2026-05-17, 160 passed, 5 warnings
- 프론트엔드: 2026-05-17, 27 passed
- 프론트엔드 빌드: 2026-05-17, build pass

## 테스트 커버리지 범위

| 영역 | 주요 검증 |
| --- | --- |
| 인증 | API Key, Bearer token, 로그인, 회원가입, Postgres auth user store |
| 권한 | admin/member role, 관리자 화면 접근, 문서 보안등급 접근 정책 |
| 문서 | 업로드, 목록, 삭제, 재인덱싱, parser, 빈 문서, 깨진 파일, 대용량 파일 |
| 인덱싱 | 인프로세스 큐, Redis 큐, retry, 실패 상태와 실패 사유 |
| 검색 | Qdrant filter, dense retrieval, hybrid search, embedding 장애 처리 |
| 채팅 | rerank, citation 검증, 근거 부족 답변 차단, LLM 장애 처리 |
| 감사 | 감사 로그 저장, 조회 필터, CSV export |
| 운영 | dependency health, operation event, rate limit, admin operations API |
| 프론트 | 로그인, 채팅, 문서 작업, 운영 상태, 감사 로그 UI |

## 성능 측정 항목

| 항목 | 측정 방법 | 목표 기준 |
| --- | --- | --- |
| API readiness | `GET /ready` | 의존성 정상 시 200 |
| 문서 업로드 응답 | 작은 TXT 파일 업로드 | 업로드 요청은 인덱싱 완료를 기다리지 않음 |
| 인덱싱 처리 시간 | 업로드 후 `indexing_status=completed`까지 | 파일 크기, parser, embedding backend별 기록 |
| 검색 latency | `POST /v1/search` | top_k, hybrid 여부, Qdrant 상태별 기록 |
| 채팅 응답 시간 | `POST /v1/chat` | LLM 모델, token 수, context 길이별 기록 |
| 동시 요청 제한 | rate limit 활성화 후 `/v1/*` 반복 호출 | 제한 초과 시 429와 `Retry-After` |
| 장애 감지 | Qdrant, MinIO, vLLM 중지 후 `/ready` | 503 또는 degraded status 확인 |

## 로컬 측정 템플릿

| 날짜 | 환경 | 모델 | 문서 | 검색 모드 | 측정 항목 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-05-17 | Docker Compose, deterministic embedding | AI stub | TXT 1KB | dense | 백엔드 테스트 | 160 passed |
| 2026-05-17 | 로컬 Node 22 | 해당 없음 | 해당 없음 | 해당 없음 | 프론트 테스트 | 27 passed |
| 측정 예정 | Galaxy Book6 Pro | Ollama `gemma3:4b` | 포트폴리오 샘플 문서 | dense | 채팅 응답 시간 | 미측정 |
| 측정 예정 | Docker Compose | BGE-M3 endpoint | PDF/DOCX/TXT | hybrid | 검색 latency | 미측정 |

## 수동 점검 시나리오

1. `2301029 / password`로 관리자 로그인
2. `internal` TXT 문서 업로드 후 indexing status 확인
3. `restricted` 문서 업로드 후 관리자 목록에서 확인
4. `1002 / password`로 로그인 후 restricted 문서가 목록에서 제외되는지 확인
5. 검색 화면에서 문서 ID와 보안등급 필터를 적용해 chunk 확인
6. 채팅 화면에서 citation과 token usage 확인
7. 감사 로그 화면에서 질문 기록과 citation 확인
8. 운영 상태 화면에서 dependency health와 rate limit backend 확인

## 부하 테스트 후보

아래 항목은 포트폴리오 발표 전 추가 측정하면 좋습니다.

| 테스트 | 도구 후보 | 목적 |
| --- | --- | --- |
| `/v1/search` 반복 요청 | k6, hey, wrk | 검색 latency와 Qdrant 응답 확인 |
| `/v1/chat` 단일 사용자 반복 | k6, curl loop | LLM timeout과 retry 정책 확인 |
| 문서 업로드 다중 요청 | k6 multipart, Python script | Redis 큐 적재와 worker 처리량 확인 |
| rate limit 검증 | curl loop | Redis backend counter 공유 확인 |

## 현재 한계

- 실제 BGE-M3 embedding 서버와 BGE reranker 서버 기준 latency는 별도 측정이 필요합니다.
- vLLM 실제 모델 성능은 GPU, VRAM, model length, quantization 방식에 따라 크게 달라집니다.
- Docker Compose 부하 테스트 수치는 아직 저장소에 고정하지 않았습니다.
