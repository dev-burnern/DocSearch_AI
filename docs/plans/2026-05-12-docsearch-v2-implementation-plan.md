# DocSearch AI V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild DocSearch AI as a V2 on-premise RAG platform with review-friendly branches, PRs, and commit structure.

**Architecture:** V2 keeps `main` as the V1 stable line and uses `develop` as the V2 integration line. All implementation work lands through small `feat/*`, `fix/*`, and `chore/*` branches. The codebase is rebuilt in small slices so storage, indexing, retrieval, LLM serving, and frontend changes can be reviewed independently.

**Tech Stack:** FastAPI, React, TypeScript, Vite, Ant Design, PostgreSQL, Redis, Qdrant, MinIO, worker queue, vLLM, Gemma 4, Docker Compose, pytest, frontend test runner

---

## PR Roadmap

### PR 0: `chore/v2-workflow`

Scope:

- branch strategy
- PR split strategy
- V2 implementation plan

Deliverables:

- `docs/development-workflow.md`
- `docs/plans/2026-05-12-docsearch-v2-implementation-plan.md`

Commit plan:

- `docs(workflow): add v2 branching strategy`
- `docs(plan): add v2 implementation roadmap`

### PR 1: `feat/v2-scaffold`

Scope:

- create the V2 repository skeleton
- define shared config boundaries
- add test scaffolding

Target files:

- Create: `backend/`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/`
- Create: `frontend-v2/`
- Create: `frontend-v2/package.json`
- Create: `frontend-v2/src/main.tsx`
- Create: `infra/compose/docker-compose.v2.yml`

Commit plan:

- `feat(scaffold): add backend v2 app skeleton`
- `feat(scaffold): add frontend v2 shell`
- `test(scaffold): add backend and frontend test bootstrap`
- `chore(compose): add v2 compose skeleton`

### PR 2: `feat/v2-auth`

Scope:

- API key auth
- workspace request context
- auth middleware and tests

Target files:

- Create: `backend/app/auth/models.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/middleware/request_context.py`
- Create: `backend/tests/auth/test_api_key_auth.py`
- Modify: `backend/app/main.py`

Commit plan:

- `test(auth): add api key auth tests`
- `feat(auth): add api key validation service`
- `feat(auth): add request context middleware`
- `docs(auth): document auth request flow`

### PR 3: `feat/v2-ingestion`

Scope:

- document upload API
- MinIO storage adapter
- parser registry for PDF, TXT, MD

Target files:

- Create: `backend/app/documents/router.py`
- Create: `backend/app/documents/service.py`
- Create: `backend/app/parsers/base.py`
- Create: `backend/app/parsers/pdf.py`
- Create: `backend/app/parsers/text.py`
- Create: `backend/app/parsers/markdown.py`
- Create: `backend/app/storage/minio.py`
- Create: `backend/tests/documents/test_upload_api.py`
- Create: `backend/tests/parsers/test_registry.py`

Commit plan:

- `test(documents): add upload api tests`
- `feat(storage): add minio storage adapter`
- `feat(parsers): add parser registry and core parsers`
- `feat(documents): add upload service and router`

### PR 4: `feat/v2-indexing-worker`

Scope:

- queue abstraction
- in-process queue for dev
- Redis-backed worker path
- chunking and embedding orchestration

Target files:

- Create: `backend/app/jobs/base.py`
- Create: `backend/app/jobs/inprocess.py`
- Create: `backend/app/jobs/redis_queue.py`
- Create: `backend/app/indexing/pipeline.py`
- Create: `backend/app/indexing/chunker.py`
- Create: `backend/app/indexing/embedder.py`
- Create: `backend/tests/indexing/test_pipeline.py`

Commit plan:

- `test(indexing): add pipeline tests`
- `feat(indexing): add chunking and embedding pipeline`
- `feat(jobs): add queue abstraction and adapters`
- `chore(worker): add worker entrypoint`

### PR 5: `feat/v2-retrieval`

Scope:

- Qdrant adapter
- metadata filtering
- dense retrieval
- reranker integration

Target files:

- Create: `backend/app/retrieval/qdrant_store.py`
- Create: `backend/app/retrieval/filters.py`
- Create: `backend/app/retrieval/retriever.py`
- Create: `backend/app/retrieval/reranker.py`
- Create: `backend/tests/retrieval/test_filters.py`
- Create: `backend/tests/retrieval/test_retriever.py`

Commit plan:

- `test(retrieval): add filter and retriever tests`
- `feat(retrieval): add qdrant store adapter`
- `feat(retrieval): add metadata filter builder`
- `feat(rerank): add reranker integration`

### PR 6: `feat/v2-llm-gateway`

Scope:

- internal LLM proxy contract
- vLLM client
- Gemma 4 profile
- timeout and response validation

Target files:

- Create: `backend/app/llm/base.py`
- Create: `backend/app/llm/vllm_client.py`
- Create: `backend/app/llm/profiles.py`
- Create: `backend/tests/llm/test_vllm_client.py`
- Create: `backend/tests/llm/test_profiles.py`

Commit plan:

- `test(llm): add vllm client tests`
- `feat(llm): add llm gateway interfaces`
- `feat(llm): add vllm client and gemma profile`
- `fix(llm): add timeout and response validation`

### PR 7: `feat/v2-chat-api`

Scope:

- retrieval to answer orchestration
- citation builder
- chat and search API

Target files:

- Create: `backend/app/rag/context_builder.py`
- Create: `backend/app/rag/service.py`
- Create: `backend/app/api/search.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/tests/rag/test_context_builder.py`
- Create: `backend/tests/api/test_chat_api.py`

Commit plan:

- `test(chat): add chat api tests`
- `feat(rag): add context builder`
- `feat(chat): add cited answer service`
- `feat(api): add search and chat routers`

### PR 8: `feat/v2-frontend-shell`

Scope:

- frontend app shell
- upload, search, and chat entry screens
- API integration boundary

Target files:

- Create: `frontend-v2/src/app/App.tsx`
- Create: `frontend-v2/src/features/upload/`
- Create: `frontend-v2/src/features/search/`
- Create: `frontend-v2/src/features/chat/`
- Create: `frontend-v2/src/lib/api.ts`
- Create: `frontend-v2/src/lib/query-client.ts`
- Create: `frontend-v2/tests/`

Commit plan:

- `test(frontend): add app shell tests`
- `feat(frontend): add app shell and routing`
- `feat(frontend): add upload and search flows`
- `feat(frontend): add chat flow`

### PR 9: `chore/v2-observability`

Scope:

- health and readiness
- structured logs
- audit trail
- metrics hooks

Commit plan:

- `test(observability): add health endpoint tests`
- `chore(logging): add structured logging`
- `feat(audit): add audit log pipeline`
- `chore(metrics): add service metrics hooks`

### PR 10: `fix/v2-hardening`

Scope:

- auth edge cases
- storage cleanup
- retry policies
- release checklist

Commit plan:

- `test(hardening): add regression coverage`
- `fix(auth): handle invalid key and revoked key paths`
- `fix(indexing): improve retry and cleanup behavior`
- `docs(release): add v2 release checklist`

## Task 1: Workflow Baseline

**Files:**
- Create: `docs/development-workflow.md`
- Create: `docs/plans/2026-05-12-docsearch-v2-implementation-plan.md`

**Step 1: Write the workflow and PR split guidance**

- Define `main`, `develop`, and `type/*` branch rules
- Define PR sizing and commit rules
- Define the initial V2 PR sequence

**Step 2: Review branch names and commit templates**

Run:

```powershell
git branch -a
```

Expected:

- `main` exists
- `develop` exists
- the current branch is `chore/v2-workflow`

**Step 3: Commit the workflow docs**

```powershell
git add docs/development-workflow.md docs/plans/2026-05-12-docsearch-v2-implementation-plan.md
git commit -m "docs(workflow): add v2 branch strategy"
```

**Step 4: Push and open the first PR**

```powershell
git push -u origin develop
git push -u origin chore/v2-workflow
```

Expected:

- `develop` is available as the integration branch
- `chore/v2-workflow` is available as the first review branch

## Task 2: Repository Scaffold PR

**Files:**
- Create: `backend/`
- Create: `frontend-v2/`
- Create: `infra/compose/docker-compose.v2.yml`
- Test: `backend/tests/`

**Step 1: Write failing backend bootstrap tests**

- validate config load
- validate app startup
- validate health route contract

**Step 2: Run backend bootstrap tests**

Run:

```powershell
pytest backend/tests -q
```

Expected:

- FAIL because scaffold files do not exist yet

**Step 3: Add minimal backend and frontend scaffold**

- create the directories
- add minimal app bootstrap
- add minimal frontend entrypoint

**Step 4: Run tests again**

Run:

```powershell
pytest backend/tests -q
```

Expected:

- PASS for the bootstrap subset

**Step 5: Commit scaffold changes**

```powershell
git add backend frontend-v2 infra
git commit -m "feat(scaffold): add v2 repository skeleton"
```

## Task 3: Auth PR

**Files:**
- Create: `backend/app/auth/`
- Modify: `backend/app/main.py`
- Test: `backend/tests/auth/test_api_key_auth.py`

**Step 1: Write failing auth tests**

- invalid key returns `401`
- missing key returns `401`
- valid key injects workspace context

**Step 2: Run auth tests**

Run:

```powershell
pytest backend/tests/auth/test_api_key_auth.py -q
```

Expected:

- FAIL before implementation

**Step 3: Add minimal API key auth implementation**

- key validation service
- dependency or middleware
- request context storage

**Step 4: Re-run auth tests**

Run:

```powershell
pytest backend/tests/auth/test_api_key_auth.py -q
```

Expected:

- PASS

**Step 5: Commit auth changes**

```powershell
git add backend/app/auth backend/tests/auth backend/app/main.py
git commit -m "feat(auth): add api key authentication"
```

## Execution Notes

- V2 work happens from `develop`, never directly on `main`
- every PR must leave the branch in a runnable or testable state
- do not mix branch strategy changes with feature code after PR 0
- when a PR grows beyond its single concern, split it before review
