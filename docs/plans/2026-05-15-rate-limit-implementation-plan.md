# 운영 Rate Limit 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인하고 구현합니다.

**목표:** `/v1/*` API에 API Key/IP 기준 인메모리 rate limit을 적용해 기본 운영 보호 장치를 추가합니다.

**아키텍처:** `Settings`에 rate limit 설정을 추가하고, FastAPI 공통 미들웨어로 요청 제한을 수행합니다. 제한기는 시간 윈도우 안의 요청 타임스탬프를 버킷별로 보관하며, 제한 초과 시 표준 429 응답을 반환합니다.

**기술 스택:** FastAPI, Starlette Middleware, Pydantic, pytest

---

### 작업 1: 설정 테스트 추가

**파일:**
- 수정: `backend/tests/test_bootstrap.py`

**작업:**
- 개발 환경에서는 rate limit이 기본 비활성화되는 테스트를 추가합니다.
- 운영 환경에서는 rate limit이 기본 활성화되는 테스트를 추가합니다.
- 요청 수와 윈도우 초 값을 환경 변수로 재정의할 수 있는 테스트를 추가합니다.

### 작업 2: 제한기 단위 테스트 추가

**파일:**
- 생성: `backend/tests/middleware/test_rate_limit.py`

**작업:**
- 허용량 안의 요청은 통과하는 테스트를 추가합니다.
- 허용량 초과 시 `retry_after_seconds`가 계산되는 테스트를 추가합니다.
- 윈도우가 지나면 같은 버킷이 다시 허용되는 테스트를 추가합니다.

### 작업 3: 미들웨어 통합 테스트 추가

**파일:**
- 수정: `backend/tests/middleware/test_rate_limit.py`

**작업:**
- `/v1/workspace`가 API Key 단위로 제한되는 테스트를 추가합니다.
- API Key가 없으면 IP 단위로 제한되는 테스트를 추가합니다.
- `/health`, `/ready` 같은 운영 엔드포인트는 제한 대상에서 제외되는 테스트를 추가합니다.

### 작업 4: 설정 구현

**파일:**
- 수정: `backend/app/core/config.py`

**작업:**
- `rate_limit_enabled`, `rate_limit_requests`, `rate_limit_window_seconds` 설정을 추가합니다.
- 운영 환경 기본값은 활성화, 개발 환경 기본값은 비활성화로 둡니다.

### 작업 5: rate limit 미들웨어 구현

**파일:**
- 생성: `backend/app/middleware/rate_limit.py`
- 수정: `backend/app/main.py`

**작업:**
- API Key/IP 기준 버킷 키를 생성합니다.
- `/v1/*`만 제한하고 나머지 경로는 통과시킵니다.
- 제한 초과 시 HTTP 429와 관련 헤더를 반환합니다.
- 정상 응답에도 rate limit 상태 헤더를 추가합니다.

### 작업 6: 문서와 실행 설정 반영

**파일:**
- 수정: `README.md`
- 수정: `.env.example`
- 수정: `infra/compose/docker-compose.yml`

**작업:**
- 운영 rate limit 설정 방법을 문서화합니다.
- 로컬 Compose 환경 변수에 rate limit 설정을 명시합니다.
- 현재 범위 문구에 운영 rate limit을 반영합니다.

### 작업 7: 전체 검증

**명령어:**
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`
- `git diff --check origin/develop..HEAD`

**기대 결과:**
- 백엔드와 프론트엔드 테스트가 통과합니다.
- Compose 설정이 유효합니다.
- 공백 오류가 없습니다.
