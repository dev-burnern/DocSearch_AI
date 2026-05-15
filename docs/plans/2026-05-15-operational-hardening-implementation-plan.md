# 운영 하드닝 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** 백엔드 기본 보안 헤더와 운영 준비 상태 진단을 추가합니다.

**아키텍처:** 보안 헤더는 독립 미들웨어로 분리해 모든 응답에 적용합니다. 운영 준비 상태는 `Settings`를 입력으로 받는 순수 함수에서 판정하고, `/ready` 엔드포인트는 이 결과를 HTTP 200 또는 503으로 변환합니다.

**기술 스택:** FastAPI, Starlette Middleware, Pydantic, pytest

---

### 작업 1: 운영 준비 상태 테스트 추가

**파일:**
- 수정: `backend/tests/test_bootstrap.py`

**작업:**
- `/ready`가 설정 점검 결과를 반환하는 실패 테스트를 작성합니다.
- 운영 환경에서 기본 API Key가 남아 있으면 HTTP 503을 반환하는 실패 테스트를 작성합니다.
- 운영 환경에서 `DEBUG=true`이면 HTTP 503을 반환하는 실패 테스트를 작성합니다.

### 작업 2: 운영 준비 상태 구현

**파일:**
- 수정: `backend/app/core/config.py`
- 생성: `backend/app/core/operations.py`
- 수정: `backend/app/main.py`

**작업:**
- 기본 API Key 상수를 설정 파일로 분리합니다.
- 운영 점검 결과 모델과 `build_readiness_response` 함수를 구현합니다.
- `/ready`에서 점검 결과에 따라 200 또는 503을 반환합니다.

### 작업 3: 보안 헤더 테스트 추가

**파일:**
- 수정: `backend/tests/test_bootstrap.py`

**작업:**
- `/health` 응답에 기본 보안 헤더가 포함되는 실패 테스트를 작성합니다.
- 기존 `X-Request-Id` 헤더가 유지되는지 함께 확인합니다.

### 작업 4: 보안 헤더 미들웨어 구현

**파일:**
- 생성: `backend/app/middleware/security_headers.py`
- 수정: `backend/app/main.py`

**작업:**
- 보안 헤더 미들웨어를 구현합니다.
- 앱 생성 시 미들웨어를 등록합니다.
- 기존 응답 헤더를 덮어쓰지 않도록 `setdefault` 방식으로 처리합니다.

### 작업 5: 문서와 검증

**파일:**
- 수정: `README.md`

**명령어:**
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`

**기대 결과:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 프로덕션 빌드와 Compose 설정 검증이 성공합니다.
- README 현재 범위와 다음 단계가 최신화됩니다.
