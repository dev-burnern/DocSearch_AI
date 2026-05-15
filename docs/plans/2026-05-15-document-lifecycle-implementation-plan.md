# 문서 삭제와 재인덱싱 구현 계획

> **Codex 안내:** TDD 순서를 유지합니다. 실패 테스트를 먼저 확인한 뒤 구현합니다.

**목표:** 문서 목록에서 업로드 문서를 삭제하거나 재인덱싱할 수 있게 합니다.

**아키텍처:** `DocumentService`가 문서 메타데이터 저장소, MinIO/S3 저장소, Qdrant 벡터 저장소, 인덱싱 큐를 조합합니다. 삭제는 저장 계층을 순서대로 정리하고, 재인덱싱은 기존 메타데이터와 원본 파일을 사용해 새 인덱싱 작업을 생성합니다. 프론트엔드는 `document-api` 클라이언트를 확장하고 `DocumentWorkspace` 목록 항목에서 액션을 제공합니다.

**기술 스택:** FastAPI, Pydantic, PostgreSQL, MinIO, Qdrant, React, TypeScript, Vite, Ant Design, Vitest, Testing Library, pytest

---

### 작업 1: 백엔드 저장소/벡터/스토리지 계약 테스트 추가

**파일:**
- 수정: `backend/tests/documents/test_document_store.py`
- 수정: `backend/tests/documents/test_postgres_document_store.py`
- 수정: `backend/tests/retrieval/test_qdrant_store.py`

**작업:**
- 문서 메타데이터 저장소가 문서 조회, 삭제, 업데이트를 지원하는 실패 테스트를 작성합니다.
- PostgreSQL 저장소가 조회/삭제 SQL을 실행하는 실패 테스트를 작성합니다.
- Qdrant 저장소가 특정 문서의 청크를 삭제하는 실패 테스트를 작성합니다.

### 작업 2: 백엔드 API 계약 테스트 추가

**파일:**
- 생성: `backend/tests/documents/test_lifecycle_api.py`

**작업:**
- 인증된 워크스페이스 문서를 삭제하면 스토리지, 벡터, 메타데이터가 정리되는 실패 테스트를 작성합니다.
- 다른 워크스페이스 문서는 404로 보호되는 실패 테스트를 작성합니다.
- 문서 재인덱싱이 새 작업 ID와 상태를 반환하는 실패 테스트를 작성합니다.

### 작업 3: 백엔드 삭제/재인덱싱 구현

**파일:**
- 수정: `backend/app/documents/models.py`
- 수정: `backend/app/documents/store.py`
- 수정: `backend/app/documents/postgres_store.py`
- 수정: `backend/app/documents/service.py`
- 수정: `backend/app/documents/router.py`
- 수정: `backend/app/storage/minio.py`
- 수정: `backend/app/retrieval/qdrant_store.py`

**작업:**
- `DocumentDeleteResponse` 모델을 추가합니다.
- 메타데이터 저장소에 `get_document`, `delete_document`를 추가합니다.
- 스토리지에 `delete_document`를 추가합니다.
- Qdrant 저장소에 `delete_document`를 추가합니다.
- `DocumentService.delete_document`, `DocumentService.reindex_document`를 구현합니다.

### 작업 4: 프론트 문서 액션 테스트와 구현

**파일:**
- 수정: `frontend/src/lib/document-api.ts`
- 수정: `frontend/src/lib/document-api.test.ts`
- 수정: `frontend/src/features/documents/DocumentWorkspace.tsx`
- 수정: `frontend/src/features/documents/DocumentWorkspace.test.tsx`

**작업:**
- 삭제/재인덱싱 API 클라이언트 실패 테스트를 작성합니다.
- 목록 항목의 삭제/재인덱싱 버튼이 클라이언트를 호출하고 목록 상태를 갱신하는 실패 테스트를 작성합니다.
- 버튼, 로딩, 오류 상태를 구현합니다.

### 작업 5: 검증

**명령어:**
- `python -m pytest backend/tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**기대 결과:**
- 백엔드와 프론트 테스트가 모두 통과합니다.
- 프로덕션 빌드와 Compose 설정 검증이 성공합니다.
