# 업로드 문서 목록 조회 Implementation Plan

> **For Codex:** TDD 순서를 유지합니다. 각 기능은 실패 테스트를 먼저 확인한 뒤 구현합니다.

**Goal:** 업로드된 문서를 워크스페이스 단위로 저장하고 프론트엔드에서 목록으로 확인할 수 있게 합니다.

**Architecture:** 문서 업로드 서비스가 업로드 응답을 `DocumentRecord`로 변환해 메타데이터 저장소에 기록합니다. FastAPI 라우터는 `GET /v1/documents`를 통해 인증된 워크스페이스의 문서 목록을 반환합니다. 프론트엔드는 `document-api` 클라이언트를 확장하고 `DocumentWorkspace`에서 목록 상태를 표시합니다.

**Tech Stack:** FastAPI, Pydantic, PostgreSQL, React, TypeScript, Vite, Ant Design, Vitest, Testing Library, pytest

---

### Task 1: 백엔드 문서 메타데이터 계약 추가

**Files:**
- Create: `backend/tests/documents/test_document_store.py`
- Create: `backend/tests/documents/test_document_listing_api.py`
- Modify: `backend/tests/documents/test_upload_api.py`
- Modify: `backend/app/documents/models.py`

**Steps:**
- 인메모리 저장소가 워크스페이스별 문서를 최신순으로 반환하는 실패 테스트를 작성합니다.
- `GET /v1/documents`가 인증된 워크스페이스 문서만 반환하는 실패 테스트를 작성합니다.
- 업로드 성공 시 문서 메타데이터가 저장되는 실패 테스트를 작성합니다.

### Task 2: 백엔드 저장소와 목록 API 구현

**Files:**
- Create: `backend/app/documents/store.py`
- Create: `backend/app/documents/postgres_store.py`
- Modify: `backend/app/documents/service.py`
- Modify: `backend/app/documents/router.py`
- Modify: `backend/app/core/config.py`

**Steps:**
- `DocumentRecord`, `DocumentListResponse` 모델을 추가합니다.
- `InMemoryDocumentMetadataStore`와 `PostgresDocumentMetadataStore`를 추가합니다.
- `DOCUMENT_METADATA_BACKEND` 설정으로 저장소 구현을 선택합니다.
- 문서 업로드 성공 시 메타데이터를 기록합니다.
- `GET /v1/documents` 목록 API를 추가합니다.

### Task 3: 프론트 API 클라이언트와 화면 추가

**Files:**
- Modify: `frontend/src/lib/document-api.ts`
- Modify: `frontend/src/lib/document-api.test.ts`
- Modify: `frontend/src/features/documents/DocumentWorkspace.tsx`
- Modify: `frontend/src/features/documents/DocumentWorkspace.test.tsx`

**Steps:**
- 목록 API 클라이언트 실패 테스트를 작성합니다.
- 문서 목록 조회 화면 실패 테스트를 작성합니다.
- 목록 조회 버튼, 오류, 빈 상태, 문서 리스트를 구현합니다.

### Task 4: 실행 설정과 문서 갱신

**Files:**
- Modify: `.env.example`
- Modify: `infra/compose/docker-compose.yml`
- Modify: `README.md`

**Steps:**
- Compose 기본값에 PostgreSQL 문서 메타데이터 저장소를 추가합니다.
- README 현재 범위와 다음 단계를 갱신합니다.

### Task 5: 검증

**Commands:**
- `python -m pytest backend/tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Expected:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 프로덕션 빌드와 Compose 설정 검증이 성공합니다.
