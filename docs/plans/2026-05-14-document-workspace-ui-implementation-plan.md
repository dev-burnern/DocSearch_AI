# 문서 작업 화면 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 문서 업로드와 검색을 프론트엔드에서 수행할 수 있게 합니다.

**Architecture:** 백엔드에는 기존 retrieval 경계를 재사용하는 `/v1/search` 라우터를 추가합니다. 프론트엔드는 `DocumentWorkspace`가 업로드/검색 상태를 담당하고, `document-api`와 `search-api` 모듈이 FastAPI 계약 변환을 담당합니다.

**Tech Stack:** FastAPI, Pydantic, Qdrant retriever, React, TypeScript, Vite, Ant Design, Vitest, Testing Library, pytest

---

### Task 1: 백엔드 검색 API 계약 추가

**Files:**
- Create: `backend/tests/search/test_search_router.py`
- Create: `backend/app/search/models.py`
- Create: `backend/app/search/router.py`
- Modify: `backend/app/main.py`

**Steps:**
- API Key 인증 후 `POST /v1/search`가 검색 결과를 반환하는 실패 테스트를 작성합니다.
- API Key가 없으면 401을 반환하는 테스트를 작성합니다.
- `SearchRequest`, `SearchResponse`, `SearchResultChunk` 모델을 추가합니다.
- 기존 `DenseRetriever`를 주입해 검색 결과를 반환합니다.

### Task 2: 문서/검색 프론트 API 클라이언트 추가

**Files:**
- Create: `frontend/src/lib/document-api.ts`
- Create: `frontend/src/lib/document-api.test.ts`
- Create: `frontend/src/lib/search-api.ts`
- Create: `frontend/src/lib/search-api.test.ts`

**Steps:**
- 업로드 API가 `FormData`와 `X-API-Key`를 전송하는 실패 테스트를 작성합니다.
- 검색 API가 `/v1/search` 요청 바디를 변환하는 실패 테스트를 작성합니다.
- API 오류 메시지를 사용자 오류로 변환합니다.

### Task 3: 문서 작업 화면 추가

**Files:**
- Create: `frontend/src/features/documents/DocumentWorkspace.tsx`
- Create: `frontend/src/features/documents/DocumentWorkspace.test.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/styles.css`

**Steps:**
- `문서` 탭 전환 실패 테스트를 작성합니다.
- 파일 업로드 성공 결과 표시 실패 테스트를 작성합니다.
- 검색 성공 결과 표시 실패 테스트를 작성합니다.
- 화면과 스타일을 구현합니다.

### Task 4: 문서 갱신과 검증

**Files:**
- Modify: `README.md`

**Commands:**
- `python -m pytest backend/tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Expected:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 프로덕션 빌드와 Compose 설정 검증이 성공합니다.
