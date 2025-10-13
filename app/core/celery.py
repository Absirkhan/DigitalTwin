"""
Celery configuration for background tasks
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "digitaltwin",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.services.meeting_automation",
        "app.services.voice_processing",
        "app.services.ai_responses"
    ]
)

# Import beat schedule
from app.services.celery_beat_config import beat_schedule

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    beat_schedule=beat_schedule,  # Add beat schedule
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',  # Use database scheduler if available
)