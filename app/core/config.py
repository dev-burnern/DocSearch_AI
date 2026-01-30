"""
Enhanced configuration for DocSearch AI
온프레미스 전용 문서 검색형 RAG 서버 설정
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===================
    # Application
    # ===================
    app_name: str = "DocSearch AI"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    @property
    def is_production(self) -> bool:
        """Check if environment is production"""
        return self.environment == "production"
    
    # ===================
    # Security
    # ===================
    secret_key: str = Field(default="change-me-in-production-use-256bit-key")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    api_key: str | None = None
    allowed_hosts: list[str] = ["*"]
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Encryption for sensitive data
    encryption_key: str = Field(default="32-byte-encryption-key-here!!")
    
    # ===================
    # Database
    # ===================
    database_url: str = "postgresql+asyncpg://docsearch:docsearch@localhost:5432/docsearch"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # ===================
    # Redis
    # ===================
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # 1 hour
    
    # ===================
    # Qdrant Vector DB
    # ===================
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "documents"
    qdrant_sparse_collection: str = "documents"  # Same collection, different vector
    vector_size: int = 1024  # BGE-M3 dense dimension
    
    # ===================
    # MinIO Object Storage
    # ===================
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "docsearch"
    minio_secure: bool = False
    
    # ===================
    # Embedding Model
    # ===================
    embed_model: str = "BAAI/bge-m3"
    embed_device: str = "cuda"  # cuda, cpu, or mps
    embed_use_fp16: bool = True
    embed_batch_size: int = 32
    embed_max_length: int = 8192
    
    # ===================
    # Reranker Model
    # ===================
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_batch_size: int = 32
    rerank_use_fp16: bool = True
    
    # ===================
    # LLM (Ollama)
    # ===================
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 8192
    ollama_timeout: int = 120
    
    # ===================
    # Retrieval
    # ===================
    retrieval_dense_top_k: int = 50
    retrieval_sparse_top_k: int = 50
    retrieval_final_top_n: int = 5
    retrieval_use_rerank: bool = True
    retrieval_use_hybrid: bool = True
    retrieval_rrf_k: int = 60  # RRF constant
    
    # ===================
    # Chunking
    # ===================
    chunk_max_chars: int = 1000
    chunk_overlap_chars: int = 200
    chunk_respect_sentences: bool = True
    
    # ===================
    # OCR
    # ===================
    ocr_enabled: bool = True
    ocr_lang: str = "korean"  # korean, english, mixed
    ocr_use_gpu: bool = True
    
    # ===================
    # ASR (Speech Recognition)
    # ===================
    asr_enabled: bool = False
    asr_model: str = "base"  # tiny, base, small, medium
    asr_device: str = "cuda"
    
    # ===================
    # File Processing
    # ===================
    max_file_size_mb: int = 100
    allowed_extensions: list[str] = [
        ".pdf", ".docx", ".xlsx", ".xlsm", ".pptx",
        ".txt", ".md", ".hwp",
        ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
        ".mp4", ".mp3", ".wav", ".m4a"
    ]
    upload_dir: Path = Path("/tmp/docsearch_uploads")
    
    # ===================
    # Celery
    # ===================
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # ===================
    # Monitoring
    # ===================
    enable_metrics: bool = True
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    @field_validator("upload_dir", mode="before")
    @classmethod
    def create_upload_dir(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v):
        if len(v) != 32:
            # Pad or truncate to 32 bytes
            v = (v * 3)[:32]
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
