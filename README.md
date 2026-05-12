# DocSearch AI

DocSearch AI is an on-premise document search and RAG platform for internal knowledge bases.

The `main` branch keeps the original prototype. The `develop` branch is the new product baseline built around a clean service architecture:

- `frontend`: React + TypeScript + Vite + Ant Design
- `gateway`: Nginx reverse proxy
- `backend`: FastAPI API server
- `worker`: async indexing worker scaffold
- `postgres`: metadata database
- `redis`: cache and job queue
- `qdrant`: vector database
- `minio`: object storage
- `llm`: local inference endpoint

## Repository Layout

```text
backend/             FastAPI service scaffold
frontend/            React web application scaffold
infra/compose/       Docker Compose runtime layout
infra/nginx/         Gateway configuration
docs/                Design and planning documents
```

## Quick Start

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

Local endpoints:

- App gateway: `http://localhost:8080`
- Backend docs: `http://localhost:8000/docs`
- Frontend dev server: `http://localhost:5173`
- MinIO console: `http://localhost:9001`

## Current Scope

The current baseline establishes service boundaries, health endpoints, local runtime config, CI, and API key based workspace context. Document ingestion, indexing, retrieval, and cited chat flows will land in follow-up branches.
