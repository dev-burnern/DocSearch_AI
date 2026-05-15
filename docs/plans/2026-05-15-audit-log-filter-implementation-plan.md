# 감사 로그 조회 필터 Implementation Plan

> **For Codex:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**Goal:** 감사 로그 API와 프론트엔드 화면에서 조건 필터를 사용할 수 있게 합니다.

**Architecture:** `ChatAuditEventFilters` 모델을 추가하고, 라우터가 쿼리 파라미터를 필터 모델로 변환합니다. 저장소 인터페이스는 워크스페이스 ID와 필터를 받아 같은 계약으로 동작합니다. 프론트엔드 `audit-log-api`는 선택 필터를 URL 쿼리로 직렬화합니다.

**Tech Stack:** FastAPI, Pydantic, PostgreSQL JSONB, React, TypeScript, Vite, Ant Design, Vitest, Testing Library, pytest

---

### Task 1: 백엔드 필터 계약 테스트 추가

**Files:**
- Modify: `backend/tests/audit/test_audit_store.py`
- Modify: `backend/tests/audit/test_postgres_store.py`
- Modify: `backend/tests/audit/test_audit_router.py`

**Steps:**
- 인메모리 저장소가 검색어, 문서 ID, 요청 ID, 시각 범위, limit을 적용하는 실패 테스트를 작성합니다.
- PostgreSQL 저장소가 필터 조건을 SQL 파라미터로 전달하는 실패 테스트를 작성합니다.
- API가 쿼리 파라미터를 저장소 필터로 넘기는 실패 테스트를 작성합니다.

### Task 2: 백엔드 필터 구현

**Files:**
- Modify: `backend/app/audit/models.py`
- Modify: `backend/app/audit/store.py`
- Modify: `backend/app/audit/postgres_store.py`
- Modify: `backend/app/audit/router.py`

**Steps:**
- `ChatAuditEventFilters` 모델을 추가합니다.
- 인메모리 저장소에 필터링 함수를 추가합니다.
- PostgreSQL 저장소에 동적 WHERE 조건을 추가합니다.
- 라우터에 `query`, `document_id`, `request_id`, `from`, `to`, `limit` 쿼리를 추가합니다.

### Task 3: 프론트 필터 계약 테스트 추가

**Files:**
- Modify: `frontend/src/lib/audit-log-api.test.ts`
- Modify: `frontend/src/features/audit/AuditLogWorkspace.test.tsx`

**Steps:**
- API 클라이언트가 필터를 쿼리 문자열로 직렬화하는 실패 테스트를 작성합니다.
- 감사 로그 화면이 입력 필터를 `listChatEvents`에 전달하는 실패 테스트를 작성합니다.

### Task 4: 프론트 필터 화면 구현

**Files:**
- Modify: `frontend/src/lib/audit-log-api.ts`
- Modify: `frontend/src/features/audit/AuditLogWorkspace.tsx`
- Modify: `frontend/src/styles.css`

**Steps:**
- `AuditLogRequest`에 선택 필터를 추가합니다.
- 조회 조건 패널에 필터 입력과 조회 개수 입력을 추가합니다.
- 빈 값은 API 요청에서 제외합니다.

### Task 5: 검증

**Commands:**
- `python -m pytest backend/tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Expected:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 프로덕션 빌드와 Compose 설정 검증이 성공합니다.
