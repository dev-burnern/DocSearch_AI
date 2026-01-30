from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Qdrant
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "doc_chunks_v1"
    vector_size: int = 1024  # BGE-M3 dense_vecs dimension

    # Embedding / Reranker
    embed_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"  # 한국어 특화 쓰려면 여기만 교체
    device: str = "cuda"  # "cuda" or "cpu"
    use_fp16: bool = True

    # Retrieval
    dense_top_k: int = 50
    final_top_n: int = 5
    rerank_batch_size: int = 32

    # Chunking
    chunk_max_chars: int = 1400
    chunk_overlap_chars: int = 200

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = 0.2
    ollama_num_ctx: int = 8192

    # Optional API auth
    api_key: str | None = None  # set하면 X-API-Key 필요


settings = Settings()
