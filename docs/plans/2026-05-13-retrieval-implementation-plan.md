# Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Qdrant 저장/조회 경계와 메타데이터 필터, Dense Retrieval 서비스를 추가한다.

**Architecture:** 인덱싱 파이프라인이 청크 임베딩을 `QdrantVectorStore`에 저장하고, `DenseRetriever`가 같은 저장소를 조회한다. 필터 계층은 워크스페이스와 문서 ID 조건을 Qdrant 전용 필터로 변환한다.

**Tech Stack:** FastAPI, pytest, qdrant-client, Docker Compose

---

### Task 1: Retrieval 테스트 추가

**Files:**
- Create: `backend/tests/retrieval/test_filters.py`
- Create: `backend/tests/retrieval/test_qdrant_store.py`
- Create: `backend/tests/retrieval/test_retriever.py`
- Modify: `backend/tests/indexing/test_pipeline.py`

**Step 1: Write the failing test**

- 메타데이터 필터가 워크스페이스와 문서 조건을 만든다.
- Qdrant 저장소가 청크를 저장하고 다시 검색한다.
- Dense retriever가 같은 워크스페이스 안에서 관련 청크를 반환한다.

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\retrieval -q`

**Step 3: Write minimal implementation**

- 실패 원인 확인만 하고 구현은 다음 태스크에서 진행

**Step 4: Run test to verify it fails correctly**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\retrieval -q`

**Step 5: Commit**

```bash
git commit -m "test(retrieval): Qdrant 저장과 검색 테스트 추가"
```

### Task 2: Qdrant 저장소와 필터 구현

**Files:**
- Create: `backend/app/retrieval/filters.py`
- Create: `backend/app/retrieval/qdrant_store.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

**Step 1: Implement filter model**

- `RetrievalFilter`
- `build_qdrant_filter()`

**Step 2: Implement vector store**

- 컬렉션 생성 보장
- 청크 upsert
- dense search

**Step 3: Run focused tests**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\retrieval\test_filters.py backend\tests\retrieval\test_qdrant_store.py -q`

**Step 4: Commit**

```bash
git commit -m "feat(retrieval): Qdrant 저장소와 필터 추가"
```

### Task 3: 인덱싱과 Dense Retriever 연결

**Files:**
- Create: `backend/app/retrieval/retriever.py`
- Modify: `backend/app/indexing/pipeline.py`
- Modify: `backend/app/indexing/embedder.py`
- Modify: `backend/app/documents/router.py`

**Step 1: Implement retriever**

- 질의 임베딩
- 저장소 검색
- 검색 결과 모델 정리

**Step 2: Update indexing pipeline**

- 임베딩 벡터를 결과 객체에 포함
- Qdrant 저장소에 청크 저장

**Step 3: Run focused tests**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\indexing\test_pipeline.py backend\tests\retrieval\test_retriever.py -q`

**Step 4: Commit**

```bash
git commit -m "feat(retrieval): 인덱싱과 Dense retriever 연결"
```

### Task 4: 문서와 전체 검증 정리

**Files:**
- Modify: `README.md`

**Step 1: Update docs**

- `vLLM` 표기 정리
- retrieval 기준선 설명 추가

**Step 2: Run full verification**

Run:
- `& .\.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Step 3: Commit**

```bash
git commit -m "docs(retrieval): 검색 기준선 문서 정리"
```
