# 관리자 운영 상태 화면 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 관리자 전용 운영 상태 API와 프론트엔드 운영 상태 탭을 추가합니다.

**Architecture:** 백엔드는 기존 readiness 빌더를 재사용하는 `/v1/admin/operations` 엔드포인트를 추가합니다. 프론트엔드는 admin 역할에서만 운영 상태 탭을 표시하고, 새 API 클라이언트와 화면 컴포넌트로 상태 요약과 점검 결과를 렌더링합니다.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Ant Design, pytest, Vitest

---

### Task 1: 백엔드 운영 상태 API 테스트

**Files:**
- Create: `backend/tests/admin/test_operations_router.py`

**Step 1: Write the failing test**

관리자 API Key로 `GET /v1/admin/operations`를 호출하면 readiness 상태, 워크스페이스 정보, rate limit 설정 요약이 반환되는 테스트를 작성합니다.

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`

Expected: `ModuleNotFoundError` 또는 404로 실패합니다.

**Step 3: Write minimal implementation**

`backend/app/admin/operations.py`에 라우터와 응답 모델을 추가하고 `backend/app/main.py`에 라우터를 등록합니다.

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`

Expected: PASS

### Task 2: 권한과 민감 정보 보호 테스트

**Files:**
- Modify: `backend/tests/admin/test_operations_router.py`

**Step 1: Write the failing test**

일반 사용자 API Key는 403을 받고, 응답 설정 요약에 API Key, DB URL, Secret 값이 없는지 확인합니다.

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`

Expected: 새 요구사항이 아직 구현되지 않아 실패합니다.

**Step 3: Write minimal implementation**

응답 모델을 안전한 필드만 포함하도록 정리하고, `require_admin_workspace_context`를 의존성으로 사용합니다.

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`

Expected: PASS

### Task 3: 프론트 API 클라이언트 테스트

**Files:**
- Create: `frontend/src/lib/operations-api.test.ts`
- Create: `frontend/src/lib/operations-api.ts`

**Step 1: Write the failing test**

`createOperationsApiClient`가 `/v1/admin/operations`로 `X-API-Key` 헤더를 보내고, 오류 응답의 `detail.message`를 예외 메시지로 사용하는 테스트를 작성합니다.

**Step 2: Run test to verify it fails**

Run: `npm test -- operations-api.test.ts`

Expected: 모듈이 없어 실패합니다.

**Step 3: Write minimal implementation**

운영 상태 응답 타입, 클라이언트 인터페이스, 오류 처리 함수를 구현합니다.

**Step 4: Run test to verify it passes**

Run: `npm test -- operations-api.test.ts`

Expected: PASS

### Task 4: 운영 상태 화면 테스트와 구현

**Files:**
- Create: `frontend/src/features/operations/OperationsStatusWorkspace.test.tsx`
- Create: `frontend/src/features/operations/OperationsStatusWorkspace.tsx`
- Modify: `frontend/src/styles.css`

**Step 1: Write the failing test**

조회 성공 시 전체 상태, 설정 요약, 점검 목록을 표시하고, 오류 시 Alert를 표시하는 테스트를 작성합니다.

**Step 2: Run test to verify it fails**

Run: `npm test -- OperationsStatusWorkspace.test.tsx`

Expected: 컴포넌트가 없어 실패합니다.

**Step 3: Write minimal implementation**

기존 감사 로그 화면 패턴을 따라 조회 패널과 결과 패널을 구현합니다.

**Step 4: Run test to verify it passes**

Run: `npm test -- OperationsStatusWorkspace.test.tsx`

Expected: PASS

### Task 5: App 탭 연결 테스트와 구현

**Files:**
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

**Step 1: Write the failing test**

admin 역할에서는 운영 상태 탭이 보이고, member 역할에서는 보이지 않으며, admin에서 member로 재확인하면 채팅 탭으로 돌아가는 테스트를 작성합니다.

**Step 2: Run test to verify it fails**

Run: `npm test -- App.test.tsx`

Expected: 운영 상태 탭이 아직 없어 실패합니다.

**Step 3: Write minimal implementation**

`App.tsx`에 `OperationsStatusWorkspace` 탭을 admin 전용으로 추가합니다.

**Step 4: Run test to verify it passes**

Run: `npm test -- App.test.tsx`

Expected: PASS

### Task 6: 문서와 전체 검증

**Files:**
- Modify: `README.md`

**Step 1: Update docs**

현재 범위와 다음 단계 문구에 관리자 운영 상태 화면을 반영합니다.

**Step 2: Run full verification**

Run:
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`
- `git diff --check origin/develop..HEAD`

Expected: 모두 성공합니다.
