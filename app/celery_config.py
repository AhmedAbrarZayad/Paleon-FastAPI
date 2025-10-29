from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "paleon",
    broker="redis://localhost:6379/0",  # Redis as message broker
    backend="redis://localhost:6379/1"  # Redis as result backend
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # Track when task starts
    task_time_limit=30 * 60,  # Kill task if it takes > 30 minutes
    task_soft_time_limit=25 * 60,  # Warn task at 25 minutes
    worker_pool="solo",  # Use solo pool on Windows to avoid permission errors
)

# Import tasks so Celery can discover them
from app import celery_task  # Explicit import
celery_app.autodiscover_tasks(['app'])