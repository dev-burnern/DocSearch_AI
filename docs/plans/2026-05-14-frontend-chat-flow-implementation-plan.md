# 프론트엔드 채팅 플로우 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 사용자가 프론트엔드에서 API Key 기반으로 질문을 보내고 출처 포함 답변을 확인할 수 있게 합니다.

**Architecture:** `App`은 앱 셸과 채팅 작업 화면만 책임집니다. `ChatWorkspace`는 폼 상태와 결과 표시를 담당하고, `chat-api` 모듈은 FastAPI 채팅 API 계약 변환을 담당합니다.

**Tech Stack:** React, TypeScript, Vite, Ant Design, Vitest, Testing Library

---

### Task 1: 테스트 환경 추가

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`

**Steps:**
- Vitest와 Testing Library를 추가합니다.
- `npm test` 스크립트를 추가합니다.
- jsdom 환경과 Ant Design용 `matchMedia` polyfill을 설정합니다.

### Task 2: 앱 셸 계약 고정

**Files:**
- Test: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

**Steps:**
- 채팅 작업 화면의 기본 필드가 렌더링되는 실패 테스트를 작성합니다.
- 기존 스캐폴드 카드를 제거하고 `ChatWorkspace`를 기본 화면으로 연결합니다.
- 테스트를 통과시킵니다.

### Task 3: 채팅 화면 동작 구현

**Files:**
- Test: `frontend/src/features/chat/ChatWorkspace.test.tsx`
- Create: `frontend/src/features/chat/ChatWorkspace.tsx`
- Modify: `frontend/src/styles.css`

**Steps:**
- API Key, 문서 ID, 질문 입력 후 클라이언트 호출이 일어나는 실패 테스트를 작성합니다.
- 답변, 모델명, 출처 목록 표시를 구현합니다.
- 오류와 로딩 상태를 처리합니다.

### Task 4: API 클라이언트 구현

**Files:**
- Test: `frontend/src/lib/chat-api.test.ts`
- Create: `frontend/src/lib/chat-api.ts`
- Modify: `frontend/vite.config.ts`
- Modify: `.env.example`

**Steps:**
- `X-API-Key` 헤더와 `/v1/chat` 요청 바디 변환 테스트를 작성합니다.
- API 오류 메시지 변환 테스트를 작성합니다.
- 기본 경로를 `/api`로 두고 Vite 개발 서버 프록시를 추가합니다.

### Task 5: 검증

**Commands:**
- `npm test`
- `npm run build`

**Expected:**
- 모든 프론트엔드 테스트가 통과합니다.
- TypeScript와 Vite 프로덕션 빌드가 성공합니다.
