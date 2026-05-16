# 관리자 화면 표시 조건 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** 확인된 API Key 역할에 따라 프론트엔드 감사 로그 탭 노출을 제어합니다.

**아키텍처:** `workspace-api` 클라이언트가 `/v1/workspace`를 호출합니다. `App`은 API Key 확인 상태를 소유하고, 확인된 API Key와 워크스페이스 컨텍스트를 각 기능 화면에 전달합니다. 감사 로그 탭은 `role=admin`일 때만 탭 목록에 포함합니다.

**기술 스택:** React, TypeScript, Vite, Ant Design, Vitest, Testing Library

---

### 작업 1: workspace API 클라이언트 테스트 추가

**파일:**
- 생성: `frontend/src/lib/workspace-api.test.ts`

**작업:**
- `/v1/workspace` 호출 시 `X-API-Key` 헤더가 들어가는 실패 테스트를 작성합니다.
- API 오류 응답의 `detail.message`를 사용자 메시지로 변환하는 실패 테스트를 작성합니다.

### 작업 2: workspace API 클라이언트 구현

**파일:**
- 생성: `frontend/src/lib/workspace-api.ts`

**작업:**
- `WorkspaceRole`, `WorkspaceContext`, `WorkspaceClient` 타입을 정의합니다.
- `createWorkspaceApiClient`를 구현합니다.
- 기존 API 클라이언트와 같은 오류 처리 패턴을 사용합니다.

### 작업 3: 앱 셸 role 기반 탭 테스트 추가

**파일:**
- 수정: `frontend/src/app/App.test.tsx`

**작업:**
- 기본 화면에서 감사 로그 탭이 숨겨지는 실패 테스트를 작성합니다.
- admin API Key 확인 후 감사 로그 탭이 표시되는 실패 테스트를 작성합니다.
- member API Key 확인 후 감사 로그 탭이 숨겨지는 실패 테스트를 작성합니다.
- 감사 로그 탭에서 member로 재확인하면 채팅 탭으로 이동하는 실패 테스트를 작성합니다.
- 확인 실패 시 오류 메시지를 표시하는 실패 테스트를 작성합니다.

### 작업 4: 앱 셸 role 기반 탭 구현

**파일:**
- 수정: `frontend/src/app/App.tsx`
- 수정: `frontend/src/features/chat/ChatWorkspace.tsx`
- 수정: `frontend/src/features/documents/DocumentWorkspace.tsx`
- 수정: `frontend/src/features/audit/AuditLogWorkspace.tsx`

**작업:**
- `App`에서 API Key 입력, 확인 버튼, 워크스페이스 상태를 관리합니다.
- 확인된 API Key를 각 기능 화면에 prop으로 전달합니다.
- 각 기능 화면은 prop으로 받은 API Key가 있으면 내부 API Key 입력을 숨기고 해당 키를 사용합니다.
- 감사 로그 탭은 admin role에서만 탭 목록에 포함합니다.

### 작업 5: 문서와 검증

**파일:**
- 수정: `README.md`

**명령어:**
- `npm test`
- `npm run build`
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `docker compose -f infra\compose\docker-compose.yml config`
- `git diff --check origin/develop..HEAD`

**기대 결과:**
- admin 사용자는 감사 로그 탭을 볼 수 있습니다.
- member 사용자는 감사 로그 탭을 볼 수 없습니다.
- 기존 채팅/문서 기능 테스트는 유지됩니다.
