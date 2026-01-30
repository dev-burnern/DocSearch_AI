from __future__ import annotations

from pathlib import Path
from typing import Any
import time

from fastapi import Depends, FastAPI, Header, HTTPException

from .config import settings
from .models import ChatRequest, ChatResponse, ChunkHit, IngestRequest, SearchRequest, SearchResponse
from .retrieval import Pipeline

app = FastAPI(title="On-prem DocSearch (Dense + Rerank + Ollama)")
pipe = Pipeline()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest(req: IngestRequest) -> dict:
    p = Path(req.path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"path not found: {p}")
    return pipe.ingest_path(p, recursive=req.recursive)


@app.post("/search", response_model=SearchResponse, dependencies=[Depends(require_api_key)])
def search(req: SearchRequest) -> SearchResponse:
    hits, lat = pipe.search(req.query, top_k=req.top_k)
    out = []
    for h in hits:
        out.append(
            ChunkHit(
                point_id=h["point_id"],
                score=h.get("rerank_score", h.get("dense_score", 0.0)),
                doc_id=h.get("doc_id", ""),
                source=h.get("source", ""),
                page=h.get("page"),
                sheet=h.get("sheet"),
                chunk_index=int(h.get("chunk_index", -1)),
                text=h.get("text", ""),
            )
        )
    return SearchResponse(hits=out, latency_ms=lat)


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest) -> ChatResponse:
    answer, ctxs, lat = pipe.chat(req.query, top_k=req.top_k, top_n=req.top_n, model=req.model)
    cites = []
    for c in ctxs:
        cites.append(
            ChunkHit(
                point_id=c["point_id"],
                score=c.get("rerank_score", c.get("dense_score", 0.0)),
                doc_id=c.get("doc_id", ""),
                source=c.get("source", ""),
                page=c.get("page"),
                sheet=c.get("sheet"),
                chunk_index=int(c.get("chunk_index", -1)),
                text=c.get("text", ""),
            )
        )
    return ChatResponse(answer=answer, citations=cites, latency_ms=lat)


# ---------------------------
# OpenAI-compatible endpoints
# ---------------------------

@app.get("/v1/models", dependencies=[Depends(require_api_key)])
def v1_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": "docsearch-rag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
def v1_chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages") or []
    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_msg = str(m.get("content") or "")
            break
    if not user_msg.strip():
        raise HTTPException(status_code=400, detail="No user message found")

    answer, ctxs, lat = pipe.chat(
        user_msg,
        top_k=payload.get("top_k"),
        top_n=payload.get("top_n"),
        model=payload.get("model_override"),
    )

    return {
        "id": "chatcmpl-docsearch",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.get("model", "docsearch-rag"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "metadata": {"latency_ms": lat, "citations": ctxs},
    }
