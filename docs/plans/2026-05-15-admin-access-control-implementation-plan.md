# 관리자 권한 분리 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** API Key 역할을 추가하고 감사 로그 API를 관리자 전용으로 제한합니다.

**아키텍처:** 인증 모델에 역할을 추가하고 `AuthService`가 3필드/4필드 API Key 형식을 모두 파싱합니다. FastAPI 의존성은 기존 워크스페이스 인증과 관리자 인증을 분리하고, 감사 로그 라우터만 관리자 인증 의존성을 사용합니다.

**기술 스택:** FastAPI, Pydantic, pytest

---

### 작업 1: 인증 역할 테스트 추가

**파일:**
- 수정: `backend/tests/auth/test_api_key_auth.py`

**작업:**
- 4필드 API Key가 `admin` 역할로 파싱되는 실패 테스트를 작성합니다.
- 3필드 API Key가 `member` 역할로 해석되는 실패 테스트를 작성합니다.
- `/v1/workspace` 응답에 역할이 포함되는 실패 테스트를 작성합니다.

### 작업 2: 인증 역할 구현

**파일:**
- 수정: `backend/app/auth/models.py`
- 수정: `backend/app/auth/service.py`
- 수정: `backend/app/auth/dependencies.py`
- 수정: `backend/app/core/config.py`
- 수정: `backend/app/core/operations.py`

**작업:**
- `UserRole` 타입과 역할 필드를 추가합니다.
- API Key 파서가 3필드와 4필드를 모두 지원하게 합니다.
- 관리자 역할을 요구하는 `require_admin_workspace_context` 의존성을 추가합니다.
- 운영 환경에서 개발 기본 API Key가 역할 필드와 함께 남아 있어도 준비 상태 진단이 실패하게 합니다.

### 작업 3: 감사 로그 관리자 권한 테스트 추가

**파일:**
- 수정: `backend/tests/audit/test_audit_router.py`
- 수정: `backend/tests/audit/test_audit_export.py`

**작업:**
- 일반 사용자가 감사 로그 조회 API를 호출하면 403이 반환되는 실패 테스트를 작성합니다.
- 일반 사용자가 감사 로그 CSV 내보내기 API를 호출하면 403이 반환되는 실패 테스트를 작성합니다.
- 기존 감사 로그 정상 케이스는 admin API Key를 사용하도록 조정합니다.

### 작업 4: 감사 로그 라우터 권한 적용

**파일:**
- 수정: `backend/app/audit/router.py`

**작업:**
- 감사 로그 조회와 내보내기 엔드포인트의 의존성을 관리자 인증으로 변경합니다.
- 워크스페이스 범위 필터는 기존처럼 유지합니다.

### 작업 5: 문서와 검증

**파일:**
- 수정: `README.md`
- 수정: `.env.example`
- 수정: `infra/compose/docker-compose.yml`
- 수정: `backend/tests/test_bootstrap.py`

**명령어:**
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`

**기대 결과:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 기존 사용자 기능은 유지되고 감사 로그 API만 관리자 전용으로 보호됩니다.
- 로컬 실행 예시는 관리자 키와 일반 사용자 키를 함께 제공합니다.
- README 현재 범위와 다음 단계가 최신화됩니다.
