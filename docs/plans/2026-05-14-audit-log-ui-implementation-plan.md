# 감사 로그 조회 UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 프론트엔드에서 API Key 기반으로 채팅 감사 로그를 조회하고 검토할 수 있게 합니다.

**Architecture:** `App`은 탭 기반 앱 셸을 담당합니다. `AuditLogWorkspace`는 API Key 입력, 조회 상태, 이벤트 목록 표시를 담당하고, `audit-log-api` 모듈은 FastAPI 감사 로그 API 계약 변환을 담당합니다.

**Tech Stack:** React, TypeScript, Vite, Ant Design, Vitest, Testing Library

---

### Task 1: 앱 탭 계약 추가

**Files:**
- Test: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

**Steps:**
- 기본 탭이 `채팅`이고 `감사 로그` 탭으로 전환할 수 있는 실패 테스트를 작성합니다.
- 앱 셸에 Ant Design Tabs를 추가합니다.

### Task 2: 감사 로그 화면 계약 추가

**Files:**
- Test: `frontend/src/features/audit/AuditLogWorkspace.test.tsx`
- Create: `frontend/src/features/audit/AuditLogWorkspace.tsx`

**Steps:**
- API Key 입력 후 조회 버튼이 활성화되는 실패 테스트를 작성합니다.
- 조회 성공 시 이벤트 요약, 답변 미리보기, 출처 파일을 표시하는 실패 테스트를 작성합니다.
- 빈 목록과 오류 상태를 테스트합니다.

### Task 3: 감사 로그 API 클라이언트 추가

**Files:**
- Test: `frontend/src/lib/audit-log-api.test.ts`
- Create: `frontend/src/lib/audit-log-api.ts`

**Steps:**
- `X-API-Key` 헤더로 `/v1/audit-logs/chat`을 호출하는 실패 테스트를 작성합니다.
- 백엔드 오류 메시지를 사용자 메시지로 변환하는 실패 테스트를 작성합니다.
- 최소 구현으로 테스트를 통과시킵니다.

### Task 4: 스타일과 문서 갱신

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `README.md`

**Steps:**
- 감사 로그 화면의 패널, 이벤트 목록, 메타데이터 스타일을 추가합니다.
- README 현재 범위와 다음 단계를 갱신합니다.

### Task 5: 검증

**Commands:**
- `npm test`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Expected:**
- 모든 프론트엔드 테스트가 통과합니다.
- TypeScript와 Vite 프로덕션 빌드가 성공합니다.
- Compose 설정이 유효합니다.
