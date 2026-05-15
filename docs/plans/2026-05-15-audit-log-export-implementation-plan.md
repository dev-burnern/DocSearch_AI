# 감사 로그 내보내기 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** 감사 로그 화면에서 현재 필터 조건의 채팅 감사 로그를 CSV로 내려받을 수 있게 합니다.

**아키텍처:** 감사 로그 조회 저장소 계약은 그대로 사용하고, 라우터에서 필터를 구성한 뒤 CSV 직렬화 계층으로 전달합니다. 프론트엔드는 `audit-log-api` 클라이언트에 내보내기 메서드를 추가하고 `AuditLogWorkspace`에서 다운로드 함수를 주입 가능하게 연결합니다.

**기술 스택:** FastAPI, Pydantic, Python csv, React, TypeScript, Ant Design, Vitest, Testing Library, pytest

---

### 작업 1: 백엔드 CSV 내보내기 계약 테스트 추가

**파일:**
- 생성: `backend/tests/audit/test_audit_export.py`
- 수정: `backend/tests/audit/test_audit_router.py`

**작업:**
- CSV 직렬화가 헤더와 이벤트 행을 생성하는 실패 테스트를 작성합니다.
- 쉼표, 줄바꿈, 따옴표가 있는 질문/답변이 CSV로 안전하게 보존되는 실패 테스트를 작성합니다.
- `GET /v1/audit-logs/chat/export`가 워크스페이스 인증과 필터를 적용하는 실패 테스트를 작성합니다.

### 작업 2: 백엔드 CSV 내보내기 구현

**파일:**
- 생성: `backend/app/audit/export.py`
- 수정: `backend/app/audit/router.py`

**작업:**
- `build_chat_audit_csv(events)` 함수를 구현합니다.
- 이벤트의 문서 ID와 출처 파일은 세미콜론으로 합칩니다.
- 라우터에 `GET /v1/audit-logs/chat/export`를 추가하고 `text/csv; charset=utf-8` 응답과 파일명 헤더를 반환합니다.

### 작업 3: 프론트 API 클라이언트 테스트와 구현

**파일:**
- 수정: `frontend/src/lib/audit-log-api.test.ts`
- 수정: `frontend/src/lib/audit-log-api.ts`

**작업:**
- `exportChatEvents`가 조회 필터를 쿼리 문자열로 보내는 실패 테스트를 작성합니다.
- 응답 본문과 `Content-Disposition` 파일명을 반환하는 실패 테스트를 작성합니다.
- API 오류 메시지 변환은 기존 조회와 같은 방식으로 처리합니다.

### 작업 4: 프론트 화면 테스트와 구현

**파일:**
- 수정: `frontend/src/features/audit/AuditLogWorkspace.test.tsx`
- 수정: `frontend/src/features/audit/AuditLogWorkspace.tsx`

**작업:**
- `CSV 내보내기` 버튼이 API Key와 필터를 사용해 클라이언트를 호출하는 실패 테스트를 작성합니다.
- 내보내기 성공 시 다운로드 함수가 파일명, 내용, MIME 타입을 받는 실패 테스트를 작성합니다.
- 내보내기 로딩과 오류 상태를 구현합니다.

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
- README 현재 범위에 감사 로그 CSV 내보내기가 반영됩니다.
