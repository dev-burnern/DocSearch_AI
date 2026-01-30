"""
Celery Tasks
문서 처리, 임베딩 생성 등 비동기 작업
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_text
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    JobStatus,
    JobType,
    ProcessingJob,
)
from app.extraction import extract_text_from_file, ExtractionResult
from app.chunking import chunk_text, Chunk
from app.search import get_embedding_service, get_vector_store
from app.services.storage import get_storage_service
from app.worker import celery_app


def get_sync_session():
    """Get synchronous database session for Celery tasks"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Convert async URL to sync
    sync_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, max_retries=3)
def process_document(self, document_id: str, storage_key: str) -> dict[str, Any]:
    """
    Main document processing pipeline
    
    1. Download from storage
    2. Extract text
    3. Create chunks
    4. Generate embeddings
    5. Store in vector DB
    
    Args:
        document_id: UUID of the document
        storage_key: MinIO storage key
    
    Returns:
        Processing result summary
    """
    session = get_sync_session()
    
    try:
        # Get document
        doc = session.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        ).scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        
        # Update status
        doc.status = DocumentStatus.PROCESSING
        session.commit()
        
        # Create processing job
        job = ProcessingJob(
            document_id=doc.id,
            job_type=JobType.EXTRACT,
            status=JobStatus.RUNNING,
            celery_task_id=self.request.id,
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        session.commit()
        
        # 1. Download file
        storage = get_storage_service()
        file_data = storage.download_file(storage_key)
        
        # 2. Extract text
        update_job_progress(session, job.id, 20, "텍스트 추출 중...")
        
        extraction = extract_text_from_file(doc.filename, file_data)
        
        # Update document metadata from extraction
        if extraction.title:
            doc.title = extraction.title
        if extraction.author:
            doc.author = extraction.author
        if extraction.page_count:
            doc.page_count = extraction.page_count
        if extraction.metadata:
            doc.metadata = extraction.metadata
        
        # 3. Create chunks
        update_job_progress(session, job.id, 40, "청크 생성 중...")
        
        all_chunks: list[Chunk] = []
        for unit in extraction.units:
            chunks = chunk_text(
                unit.text,
                page=unit.page,
                sheet=unit.sheet,
                slide=unit.slide,
                heading=unit.heading,
                is_table=unit.is_table,
            )
            all_chunks.extend(chunks)
        
        if not all_chunks:
            raise RuntimeError("No chunks created from document")
        
        # 4. Generate embeddings
        update_job_progress(session, job.id, 60, "임베딩 생성 중...")
        
        embedding_service = get_embedding_service()
        texts = [c.text for c in all_chunks]
        embeddings = embedding_service.encode_documents(
            texts,
            return_dense=True,
            return_sparse=True,
        )
        
        # 5. Prepare points for vector DB
        update_job_progress(session, job.id, 80, "벡터 저장 중...")
        
        vector_store = get_vector_store()
        points = []
        chunk_records = []
        
        for i, chunk in enumerate(all_chunks):
            point_id = str(uuid.uuid4())
            
            # Prepare vector point
            point = {
                "id": point_id,
                "dense": embeddings["dense"][i],
                "sparse": embeddings["sparse"][i],
                "payload": {
                    "doc_id": str(doc.id),
                    "chunk_id": point_id,
                    "source": doc.filename,
                    "filename": doc.filename,
                    "page": chunk.page,
                    "sheet": chunk.sheet,
                    "slide": chunk.slide,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "heading": chunk.heading,
                    "has_table": chunk.has_table,
                    "department_id": str(doc.department_id) if doc.department_id else None,
                    "project_id": str(doc.project_id) if doc.project_id else None,
                    "classification": doc.classification.value,
                    "doc_type": Path(doc.filename).suffix.lower().lstrip("."),
                    "uploaded_at": int(doc.created_at.timestamp()),
                },
            }
            points.append(point)
            
            # Prepare chunk record
            chunk_record = DocumentChunk(
                id=uuid.UUID(point_id),
                document_id=doc.id,
                chunk_index=i,
                text=chunk.text,
                text_hash=hash_text(chunk.text),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                page_number=chunk.page,
                sheet_name=chunk.sheet,
                slide_number=chunk.slide,
                qdrant_point_id=point_id,
                heading=chunk.heading,
                has_table=chunk.has_table,
            )
            chunk_records.append(chunk_record)
        
        # 6. Store in vector DB
        vector_store.upsert_points(points)
        
        # 7. Store chunk records in PostgreSQL
        session.add_all(chunk_records)
        
        # 8. Update document status
        doc.status = DocumentStatus.READY
        doc.chunk_count = len(all_chunks)
        
        # 9. Complete job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        
        session.commit()
        
        return {
            "document_id": document_id,
            "chunks_created": len(all_chunks),
            "status": "completed",
        }
        
    except Exception as e:
        session.rollback()
        
        # Update document status
        doc = session.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        ).scalar_one_or_none()
        
        if doc:
            doc.status = DocumentStatus.ERROR
            doc.error_message = str(e)
        
        # Update job status (get first one if multiple exist)
        job = session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.celery_task_id == self.request.id)
            .order_by(ProcessingJob.created_at.desc())
        ).scalars().first()
        
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
        
        session.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def reindex_document(self, document_id: str) -> dict[str, Any]:
    """
    Re-index an existing document
    Useful when embedding model changes
    """
    session = get_sync_session()
    
    try:
        doc = session.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        ).scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        
        # Get existing chunks
        chunks = session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index)
        ).scalars().all()
        
        if not chunks:
            raise ValueError(f"No chunks found for document: {document_id}")
        
        # Delete existing vectors
        vector_store = get_vector_store()
        vector_store.delete_by_doc_id(str(doc.id))
        
        # Re-embed
        embedding_service = get_embedding_service()
        texts = [c.text for c in chunks]
        embeddings = embedding_service.encode_documents(
            texts,
            return_dense=True,
            return_sparse=True,
        )
        
        # Create new points
        points = []
        for i, chunk in enumerate(chunks):
            point = {
                "id": chunk.qdrant_point_id,
                "dense": embeddings["dense"][i],
                "sparse": embeddings["sparse"][i],
                "payload": {
                    "doc_id": str(doc.id),
                    "chunk_id": chunk.qdrant_point_id,
                    "source": doc.filename,
                    "filename": doc.filename,
                    "page": chunk.page_number,
                    "sheet": chunk.sheet_name,
                    "slide": chunk.slide_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "heading": chunk.heading,
                    "has_table": chunk.has_table,
                    "department_id": str(doc.department_id) if doc.department_id else None,
                    "project_id": str(doc.project_id) if doc.project_id else None,
                    "classification": doc.classification.value,
                    "doc_type": Path(doc.filename).suffix.lower().lstrip("."),
                    "uploaded_at": int(doc.created_at.timestamp()),
                },
            }
            points.append(point)
        
        vector_store.upsert_points(points)
        
        return {
            "document_id": document_id,
            "chunks_reindexed": len(chunks),
            "status": "completed",
        }
        
    except Exception as e:
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        session.close()


@celery_app.task
def delete_document_vectors(document_id: str) -> dict[str, Any]:
    """Delete all vectors for a document"""
    vector_store = get_vector_store()
    vector_store.delete_by_doc_id(document_id)
    
    return {
        "document_id": document_id,
        "status": "deleted",
    }


def update_job_progress(session: Session, job_id: uuid.UUID, progress: int, message: str = "") -> None:
    """Update job progress"""
    job = session.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()
    
    if job:
        job.progress = progress
        if message:
            job.error_message = message  # Reusing for status message
        session.commit()
