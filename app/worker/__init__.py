"""
Celery Worker Configuration
비동기 작업 처리를 위한 Celery 설정
"""
from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "docsearch",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.worker.tasks.process_document": {"queue": "documents"},
        "app.worker.tasks.extract_text": {"queue": "documents"},
        "app.worker.tasks.create_embeddings": {"queue": "gpu"},
        "app.worker.tasks.reindex_document": {"queue": "gpu"},
    },
    
    # Concurrency
    worker_concurrency=2,  # Low concurrency for GPU tasks
    worker_prefetch_multiplier=1,  # Process one task at a time
    
    # Task execution
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    
    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    
    # Error handling
    task_annotations={
        "*": {"rate_limit": "10/m"},  # Rate limit all tasks
    },
)

# Optional: Configure periodic tasks (celery beat)
celery_app.conf.beat_schedule = {
    # "cleanup-old-jobs": {
    #     "task": "app.worker.tasks.cleanup_old_jobs",
    #     "schedule": 3600.0,  # Every hour
    # },
}
