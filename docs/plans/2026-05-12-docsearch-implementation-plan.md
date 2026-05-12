# DocSearch AI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild DocSearch AI as an on-premise RAG platform with review-friendly branches, PRs, and commits.

**Architecture:** `main` preserves the original prototype. `develop` is the rebuild integration branch. The service baseline is organized around `backend`, `frontend`, `infra`, local storage services, and a local LLM boundary. All implementation lands through small review slices.

**Tech Stack:** FastAPI, React, TypeScript, Vite, Ant Design, PostgreSQL, Redis, Qdrant, MinIO, worker queue, vLLM, Gemma 4, Docker Compose, pytest

---

## PR Roadmap

### PR 0: `chore/workflow`

Scope:

- branch strategy
- PR split strategy
- implementation roadmap

Deliverables:

- `docs/development-workflow.md`
- `docs/plans/2026-05-12-docsearch-implementation-plan.md`

### PR 1: `feat/scaffold`

Scope:

- replace the legacy service baseline on `develop`
- add the new backend bootstrap under `backend/`
- replace the web shell under `frontend/`
- add compose, gateway, and CI

Deliverables:

- `backend/`
- `frontend/`
- `infra/compose/docker-compose.yml`
- `infra/nginx/default.conf`
- `.github/workflows/ci.yml`

### PR 2: `feat/auth`

Scope:

- API key auth
- workspace request context
- protected route boundary

Target files:

- `backend/app/auth/models.py`
- `backend/app/auth/service.py`
- `backend/app/auth/dependencies.py`
- `backend/app/middleware/request_context.py`
- `backend/tests/auth/test_api_key_auth.py`
- `backend/app/main.py`

### PR 3: `feat/ingestion`

Scope:

- document upload API
- MinIO storage adapter
- parser registry for PDF, TXT, MD

Target files:

- `backend/app/documents/router.py`
- `backend/app/documents/service.py`
- `backend/app/parsers/base.py`
- `backend/app/parsers/pdf.py`
- `backend/app/parsers/text.py`
- `backend/app/parsers/markdown.py`
- `backend/app/storage/minio.py`
- `backend/tests/documents/test_upload_api.py`

### PR 4: `feat/indexing-worker`

Scope:

- queue abstraction
- in-process queue for dev
- Redis-backed worker path
- chunking and embedding orchestration

Target files:

- `backend/app/jobs/base.py`
- `backend/app/jobs/inprocess.py`
- `backend/app/jobs/redis_queue.py`
- `backend/app/indexing/pipeline.py`
- `backend/app/indexing/chunker.py`
- `backend/app/indexing/embedder.py`
- `backend/tests/indexing/test_pipeline.py`

### PR 5: `feat/retrieval`

Scope:

- Qdrant adapter
- metadata filtering
- dense retrieval
- reranker integration

Target files:

- `backend/app/retrieval/qdrant_store.py`
- `backend/app/retrieval/filters.py`
- `backend/app/retrieval/retriever.py`
- `backend/app/retrieval/reranker.py`
- `backend/tests/retrieval/test_filters.py`
- `backend/tests/retrieval/test_retriever.py`

### PR 6: `feat/llm-gateway`

Scope:

- internal LLM proxy contract
- vLLM client
- Gemma 4 profile
- timeout and response validation

Target files:

- `backend/app/llm/base.py`
- `backend/app/llm/vllm_client.py`
- `backend/app/llm/profiles.py`
- `backend/tests/llm/test_vllm_client.py`
- `backend/tests/llm/test_profiles.py`

### PR 7: `feat/chat-api`

Scope:

- retrieval to answer orchestration
- citation builder
- chat and search API

Target files:

- `backend/app/rag/context_builder.py`
- `backend/app/rag/service.py`
- `backend/app/api/search.py`
- `backend/app/api/chat.py`
- `backend/tests/rag/test_context_builder.py`
- `backend/tests/api/test_chat_api.py`

### PR 8: `feat/frontend-shell`

Scope:

- frontend app shell
- upload, search, and chat entry screens
- API integration boundary

Target files:

- `frontend/src/app/App.tsx`
- `frontend/src/features/upload/`
- `frontend/src/features/search/`
- `frontend/src/features/chat/`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/query-client.ts`

### PR 9: `chore/observability`

Scope:

- health and readiness
- structured logs
- audit trail
- metrics hooks

### PR 10: `fix/hardening`

Scope:

- auth edge cases
- storage cleanup
- retry policies
- release checklist

## Current Baseline

The scaffold PR is expected to leave the branch in this state:

- `backend` serves `/health` and `/ready`
- `frontend` builds successfully
- `infra/compose/docker-compose.yml` resolves cleanly
- `gateway` proxies `frontend` and `api`
- `worker` exists as a dedicated process boundary
- old V1 service layout no longer drives `develop`

## Execution Notes

- do all rebuild work from `develop`, never from `main`
- keep every PR runnable or testable
- use TDD for behavior changes
- keep one concern per PR
- defer extra cleanup to explicit follow-up branches
