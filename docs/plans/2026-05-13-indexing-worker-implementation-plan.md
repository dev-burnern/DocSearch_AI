# Indexing Worker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 문서 업로드 이후 인덱싱 잡을 생성하고, 개발 환경에서 청킹과 임베딩까지 연결되는 최소 인덱싱 워커 흐름을 추가한다.

**Architecture:** `DocumentService`는 저장소에 원본을 저장한 뒤 `JobQueue`에 인덱싱 잡을 전달한다. 개발 환경에서는 `InProcessJobQueue`가 `IndexingPipeline`을 즉시 실행하고, Redis 경계는 직렬화 가능한 잡 객체와 어댑터 인터페이스만 제공한다.

**Tech Stack:** FastAPI, pytest, MinIO, Redis, Docker Compose

---

### Task 1: 인덱싱 파이프라인 테스트

**Files:**
- Create: `backend/tests/indexing/test_pipeline.py`
- Create: `backend/app/indexing/pipeline.py`
- Create: `backend/app/indexing/chunker.py`
- Create: `backend/app/indexing/embedder.py`

**Step 1: Write the failing test**

- 저장소에서 원본 문서를 읽는다.
- 파서를 거쳐 텍스트를 얻는다.
- 청킹 결과와 임베딩 결과 개수가 일치한다.

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\indexing\test_pipeline.py -q`

**Step 3: Write minimal implementation**

- `IndexingPipeline`
- `CharacterChunker`
- `DeterministicEmbedder`

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\indexing\test_pipeline.py -q`

**Step 5: Commit**

```bash
git commit -m "test(indexing): 인덱싱 파이프라인 테스트 추가"
```

### Task 2: 큐 추상화와 개발용 인프로세스 큐

**Files:**
- Create: `backend/tests/jobs/test_inprocess_queue.py`
- Create: `backend/app/jobs/base.py`
- Create: `backend/app/jobs/inprocess.py`
- Create: `backend/app/jobs/redis_queue.py`

**Step 1: Write the failing test**

- 인프로세스 큐가 받은 잡을 즉시 처리한다.
- 완료 상태와 파이프라인 결과를 응답에 담는다.

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\jobs\test_inprocess_queue.py -q`

**Step 3: Write minimal implementation**

- `IndexDocumentJob`
- `JobDispatchResult`
- `JobQueue`
- `InProcessJobQueue`
- `RedisJobQueue` 골격

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\jobs\test_inprocess_queue.py -q`

**Step 5: Commit**

```bash
git commit -m "feat(indexing): 인프로세스 큐와 잡 경계 추가"
```

### Task 3: 업로드 흐름 인덱싱 연동

**Files:**
- Modify: `backend/tests/documents/test_upload_api.py`
- Modify: `backend/app/documents/models.py`
- Modify: `backend/app/documents/service.py`
- Modify: `backend/app/documents/router.py`
- Modify: `backend/app/storage/minio.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/worker.py`

**Step 1: Write the failing test**

- 업로드 응답에 인덱싱 잡 정보가 포함된다.
- 개발용 인프로세스 큐에서는 업로드 직후 완료 상태를 받는다.

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\documents\test_upload_api.py -q`

**Step 3: Write minimal implementation**

- 저장소 다운로드 메서드 추가
- `DocumentService`에서 큐 호출
- 기본 큐 의존성 연결
- 워커 엔트리포인트 로그 정리

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m pytest backend\tests\documents\test_upload_api.py -q`

**Step 5: Commit**

```bash
git commit -m "feat(documents): 업로드 이후 인덱싱 잡 생성 추가"
```

### Task 4: 문서와 실행 구성 정리

**Files:**
- Modify: `README.md`
- Modify: `.env.example`

**Step 1: Update docs**

- `llm` 표기를 `vLLM`로 교체
- 인덱싱 경계와 개발용 인프로세스 큐 설명 추가

**Step 2: Run full verification**

Run:
- `& .\.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm run build`
- `docker compose -f infra/compose/docker-compose.yml config`

**Step 3: Commit**

```bash
git commit -m "docs(indexing): 인덱싱 기준선과 vLLM 표기 정리"
```
