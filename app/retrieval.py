from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import requests
from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from .chunking import chunk_text
from .config import settings
from .text_extract import extract_text_units, normalize_text


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


class Embedder:
    def __init__(self) -> None:
        self.model = BGEM3FlagModel(
            settings.embed_model,
            use_fp16=settings.use_fp16,
            device=settings.device,
        )

    def encode_query_dense(self, q: str) -> np.ndarray:
        q = normalize_text(q)
        out = self.model.encode([q], max_length=8192)
        dense = out["dense_vecs"][0]
        return np.asarray(dense, dtype=np.float32)

    def encode_corpus_dense(self, texts: list[str]) -> np.ndarray:
        texts = [normalize_text(t) for t in texts]
        out = self.model.encode(texts, max_length=8192)
        dense = out["dense_vecs"]
        return np.asarray(dense, dtype=np.float32)


class Reranker:
    def __init__(self) -> None:
        self.model = FlagReranker(settings.rerank_model, use_fp16=settings.use_fp16)

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        query = normalize_text(query)
        scores: list[float] = []
        bs = settings.rerank_batch_size
        for i in range(0, len(passages), bs):
            batch = passages[i : i + bs]
            pairs = [[query, p] for p in batch]
            s = self.model.compute_score(pairs, normalize=True)
            scores.extend([float(x) for x in s])
        return scores


class Store:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)

    def ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if settings.qdrant_collection in existing:
            return

        self.client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qm.VectorParams(
                size=settings.vector_size,
                distance=qm.Distance.COSINE,
            ),
            hnsw_config=qm.HnswConfigDiff(m=16, ef_construct=128),
        )

        # 최소 운영 필드 인덱스(검색 결과 필터/정렬 안정화에 유리)
        self.client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="doc_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="source",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )

    def upsert(self, points: list[qm.PointStruct]) -> None:
        self.client.upsert(collection_name=settings.qdrant_collection, points=points)

    def search(self, vector: np.ndarray, limit: int) -> list[Any]:
        return self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector.tolist(),
            limit=limit,
            with_payload=True,
        )


class Pipeline:
    def __init__(self) -> None:
        self.embedder = Embedder()
        self.reranker = Reranker()
        self.store = Store()
        self.store.ensure_collection()

    def ingest_path(self, path: Path, recursive: bool = True) -> dict[str, Any]:
        t0 = time.perf_counter()
        files: list[Path] = []

        if path.is_file():
            files = [path]
        else:
            pattern = "**/*" if recursive else "*"
            for p in path.glob(pattern):
                if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md"):
                    files.append(p)

        ingested = 0
        skipped = 0

        for f in files:
            try:
                self._ingest_file(f)
                ingested += 1
            except Exception:
                skipped += 1

        return {
            "files_total": len(files),
            "files_ingested": ingested,
            "files_skipped": skipped,
            "latency_ms": (time.perf_counter() - t0) * 1000.0,
        }

    def _ingest_file(self, path: Path) -> None:
        doc_id = sha256_file(path)
        units = extract_text_units(path)

        batch_texts: list[str] = []
        batch_meta: list[dict[str, Any]] = []
        batch_points: list[qm.PointStruct] = []

        def flush() -> None:
            if not batch_texts:
                return
            vecs = self.embedder.encode_corpus_dense(batch_texts)
            for v, m in zip(vecs, batch_meta, strict=True):
                batch_points.append(
                    qm.PointStruct(id=m["id"], vector=v.tolist(), payload=m["payload"])
                )
            self.store.upsert(batch_points)
            batch_texts.clear()
            batch_meta.clear()
            batch_points.clear()

        for u in units:
            chunks = chunk_text(
                u.text,
                max_chars=settings.chunk_max_chars,
                overlap_chars=settings.chunk_overlap_chars,
            )
            for ch in chunks:
                pid = str(uuid.uuid4())
                payload = {
                    "doc_id": doc_id,
                    "source": str(path),
                    "page": u.page,
                    "sheet": u.sheet,
                    "chunk_index": ch.chunk_index,
                    "text": ch.text,
                }
                batch_texts.append(ch.text)
                batch_meta.append({"id": pid, "payload": payload})

                if len(batch_texts) >= 64:
                    flush()

        flush()

    def search(self, query: str, top_k: int | None = None) -> tuple[list[dict[str, Any]], dict[str, float]]:
        lat: dict[str, float] = {}
        t0 = time.perf_counter()

        t1 = time.perf_counter()
        qv = self.embedder.encode_query_dense(query)
        lat["embed_ms"] = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        dense_k = top_k or settings.dense_top_k
        hits = self.store.search(qv, limit=dense_k)
        lat["qdrant_ms"] = (time.perf_counter() - t2) * 1000.0

        cand = []
        passages = []
        for h in hits:
            p = h.payload or {}
            passages.append(p.get("text", ""))
            cand.append(
                {
                    "point_id": str(h.id),
                    "dense_score": float(h.score),
                    **p,
                }
            )

        t3 = time.perf_counter()
        rr_scores = self.reranker.rerank(query, passages) if passages else []
        lat["rerank_ms"] = (time.perf_counter() - t3) * 1000.0

        for c, s in zip(cand, rr_scores, strict=False):
            c["rerank_score"] = float(s)

        cand.sort(key=lambda x: x.get("rerank_score", -1.0), reverse=True)
        lat["total_ms"] = (time.perf_counter() - t0) * 1000.0
        return cand, lat

    def chat(self, query: str, top_k: int | None = None, top_n: int | None = None, model: str | None = None) -> tuple[str, list[dict[str, Any]], dict[str, float]]:
        cands, lat = self.search(query, top_k=top_k)
        n = top_n or settings.final_top_n
        top = cands[:n]

        prompt = build_prompt(query, top)
        t = time.perf_counter()
        answer = ollama_chat(prompt, model=model or settings.ollama_model)
        lat["llm_ms"] = (time.perf_counter() - t) * 1000.0
        lat["e2e_ms"] = lat.get("total_ms", 0.0) + lat["llm_ms"]
        return answer, top, lat


def build_prompt(query: str, contexts: list[dict[str, Any]]) -> str:
    blocks = []
    for i, c in enumerate(contexts, start=1):
        src = c.get("source", "")
        page = c.get("page")
        sheet = c.get("sheet")
        chunk_index = c.get("chunk_index")
        blocks.append(
            f"[{i}] source={src} page={page} sheet={sheet} chunk={chunk_index}\n{c.get('text','')}".strip()
        )
    ctx = "\n\n---\n\n".join(blocks)

    return (
        "역할: 사내 문서 검색 QA 어시스턴트.\n"
        "규칙:\n"
        "1) 아래 '근거(문서 발췌)' 안에서만 답변한다.\n"
        "2) 근거가 부족하면 '문서에서 근거를 찾을 수 없습니다'라고 말한다.\n"
        "3) 답변 끝에 반드시 인용 번호([1],[2]...)를 붙인다.\n\n"
        f"질문: {normalize_text(query)}\n\n"
        f"근거(문서 발췌):\n{ctx}\n\n"
        "답변:"
    )


def ollama_chat(prompt: str, model: str) -> str:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a grounded RAG assistant. Use only provided context and cite sources."},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": settings.ollama_temperature,
            "num_ctx": settings.ollama_num_ctx,
        },
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return (data.get("message") or {}).get("content", "").strip()
