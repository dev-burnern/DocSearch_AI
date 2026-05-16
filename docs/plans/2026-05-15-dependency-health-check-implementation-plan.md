# 외부 의존성 상태 점검 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** `/ready`가 설정 점검과 외부 의존성 연결 상태를 함께 표현할 수 있게 합니다.

**아키텍처:** `Settings`에 외부 점검 토글과 타임아웃을 추가합니다. `DependencyHealthChecker`는 실제 연결 점검을 담당하고, `build_readiness_response`는 설정 점검이 통과했을 때만 외부 점검 결과를 합칩니다.

**기술 스택:** FastAPI, Pydantic, httpx, psycopg, pytest

---

### 작업 1: 설정 토글 테스트 추가

**파일:**
- 수정: `backend/tests/test_bootstrap.py`

**작업:**
- 개발 환경에서는 외부 의존성 점검이 기본 비활성화인지 실패 테스트를 작성합니다.
- 운영 환경에서는 외부 의존성 점검이 기본 활성화되는지 실패 테스트를 작성합니다.
- 환경 변수로 점검 타임아웃을 바꿀 수 있는지 실패 테스트를 작성합니다.

### 작업 2: 설정 토글 구현

**파일:**
- 수정: `backend/app/core/config.py`

**작업:**
- `dependency_health_checks_enabled` 설정을 추가합니다.
- `dependency_health_timeout_seconds` 설정을 추가합니다.
- 운영 환경 기본값은 활성화, 개발 환경 기본값은 비활성화로 둡니다.

### 작업 3: 의존성 점검기 테스트 추가

**파일:**
- 생성: `backend/tests/core/test_dependency_health.py`

**작업:**
- PostgreSQL, Qdrant, MinIO, vLLM 점검이 성공하면 각각 `ready`를 반환하는 실패 테스트를 작성합니다.
- Redis와 BGE Reranker는 관련 백엔드가 켜진 경우에만 점검되는 실패 테스트를 작성합니다.
- 한 의존성 점검이 실패해도 나머지 점검 결과가 함께 반환되는 실패 테스트를 작성합니다.

### 작업 4: 의존성 점검기 구현

**파일:**
- 생성: `backend/app/core/dependency_health.py`

**작업:**
- `DependencyCheckResult` 모델을 정의합니다.
- `DependencyHealthChecker`를 구현합니다.
- PostgreSQL `SELECT 1`, HTTP 상태 호출, Redis `PING` 점검 함수를 추가합니다.
- 테스트에서는 probe 함수를 주입할 수 있게 설계합니다.

### 작업 5: `/ready` 통합 테스트 추가

**파일:**
- 수정: `backend/tests/test_bootstrap.py`

**작업:**
- 외부 점검이 활성화되면 `/ready` 응답에 의존성 결과가 포함되는 실패 테스트를 작성합니다.
- 외부 점검 중 하나라도 `not_ready`이면 HTTP 503을 반환하는 실패 테스트를 작성합니다.
- 설정 점검이 실패하면 외부 점검기를 호출하지 않는 실패 테스트를 작성합니다.

### 작업 6: `/ready` 통합 구현

**파일:**
- 수정: `backend/app/core/operations.py`
- 수정: `backend/app/main.py`

**작업:**
- `build_readiness_response`가 선택적으로 `DependencyHealthChecker`를 받아 의존성 결과를 합치게 합니다.
- FastAPI 앱에서 외부 점검기를 앱 상태에 등록합니다.
- `/ready` 라우트가 등록된 점검기를 사용하게 합니다.

### 작업 7: 문서와 실행 설정 반영

**파일:**
- 수정: `README.md`
- 수정: `.env.example`
- 수정: `infra/compose/docker-compose.yml`

**작업:**
- 외부 의존성 점검 환경 변수를 문서화합니다.
- Compose 실행에서는 외부 점검을 켤 수 있게 환경 변수를 명시합니다.
- 현재 범위와 다음 단계 문구를 갱신합니다.

### 작업 8: 전체 검증

**명령어:**
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`
- `git diff --check origin/develop..HEAD`

**기대 결과:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 외부 의존성 점검이 비활성화된 개발 환경에서는 기존 `/ready` 응답이 유지됩니다.
- 외부 의존성 점검이 활성화되면 `/ready`가 의존성별 상태를 반환합니다.
