"""
Celery Beat configuration for scheduled tasks
"""

from celery.schedules import crontab
from app.core.config import settings

# Celery Beat schedule
beat_schedule = {
    'auto-join-meetings': {
        'task': 'app.services.meeting_automation.auto_join_scheduler',
        'schedule': 30.0,  # Run every 30 seconds
        'options': {
            'expires': 15,  # Task expires after 15 seconds if not executed
        }
    },
    'cleanup-old-meetings': {
        'task': 'app.services.meeting_automation.cleanup_old_meetings',
        'schedule': crontab(minute=0, hour=2),  # Run daily at 2 AM
    },
}

# Celery Beat settings
beat_settings = {
    'beat_schedule': beat_schedule,
    'timezone': 'UTC',
}