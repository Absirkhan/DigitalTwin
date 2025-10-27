"""
Meeting automation service for handling digital twin meeting participation
"""

from celery import Celery
from datetime import datetime, timedelta
from typing import Optional, List
import requests
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.models.bot import Bot
from app.models.user import User
from app.schemas.meeting import MeetingJoinRequest
from app.services.recall_service import recall_service

logger = logging.getLogger(__name__)

# Initialize Celery (this would typically be configured elsewhere)
celery_app = Celery('meeting_automation')


@celery_app.task
def auto_join_scheduler():
    """
    Periodic task to check for meetings that need auto-joining
    This should be scheduled to run every 30 seconds using Celery Beat
    """
    logger.info("Running auto-join scheduler...")
    
    try:
        db = SessionLocal()
        
        # Calculate the time window for auto-joining
        now = datetime.utcnow()
        join_window_start = now
        join_window_end = now + timedelta(minutes=settings.AUTO_JOIN_ADVANCE_MINUTES)
        
        # Find meetings that need auto-joining
        meetings_to_join = db.query(Meeting).filter(
            and_(
                Meeting.auto_join == True,
                Meeting.status == "scheduled",
                Meeting.scheduled_time >= join_window_start,
                Meeting.scheduled_time <= join_window_end,
                Meeting.digital_twin_id.isnot(None)
            )
        ).all()
        
        logger.info(f"Found {len(meetings_to_join)} meetings to auto-join")
        
        for meeting in meetings_to_join:
            try:
                # Update meeting status to prevent duplicate joins
                meeting.status = "joining"
                db.commit()
                
                # Trigger the join meeting task
                join_meeting_auto.delay(
                    meeting.id,
                    meeting.digital_twin_id,
                    meeting.meeting_url,
                    meeting.platform,
                    meeting.user_id
                )
                
                logger.info(f"Scheduled auto-join for meeting {meeting.id} ({meeting.title})")
                
            except Exception as e:
                logger.error(f"Failed to schedule auto-join for meeting {meeting.id}: {str(e)}")
                # Reset status if scheduling failed
                meeting.status = "scheduled"
                db.commit()
        
        db.close()
        
    except Exception as e:
        logger.error(f"Auto-join scheduler error: {str(e)}")


@celery_app.task
def join_meeting_auto(meeting_id: int, twin_id: int, meeting_url: str, platform: str, user_id: int):
    """
    Automatically join a meeting with the digital twin using Recall AI
    """
    import asyncio
    
    async def _join_meeting_async():
        logger.info(f"Auto-joining meeting {meeting_id} with twin {twin_id}")
        
        try:
            db = SessionLocal()
            
            # Get the meeting details
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                logger.error(f"Meeting {meeting_id} not found")
                return {"status": "failed", "error": "Meeting not found"}
            
            # Get user details for bot naming
            user = db.query(User).filter(User.id == user_id).first()
            bot_name = f"{user.bot_name if user and user.bot_name else 'Digital Twin'}"
            
            # Create the join request
            join_request = MeetingJoinRequest(
                meeting_url=meeting_url,
                bot_name=bot_name,
                enable_realtime_processing=False  # Disable to avoid websocket issues
            )
            
            # Join the meeting using Recall AI
            response = await recall_service.join_meeting(join_request)
            
            if response.success and response.bot_id:
                # Update meeting status
                meeting.status = "in_progress"
                
                # Create or update bot record
                existing_bot = db.query(Bot).filter(Bot.bot_id == response.bot_id).first()
                if not existing_bot:
                    new_bot = Bot(
                        bot_id=response.bot_id,
                        user_id=user_id,
                        bot_name=bot_name,
                        platform=platform,
                        meeting_id=meeting_id
                    )
                    db.add(new_bot)
                else:
                    existing_bot.meeting_id = meeting_id
                    existing_bot.platform = platform
                
                db.commit()
                
                logger.info(f"Successfully auto-joined meeting {meeting_id} with bot {response.bot_id}")
                
                return {
                    "status": "joined",
                    "meeting_id": meeting_id,
                    "bot_id": response.bot_id,
                    "twin_id": twin_id
                }
            else:
                # Update meeting status back to scheduled if join failed
                meeting.status = "scheduled"
                db.commit()
                
                logger.error(f"Failed to auto-join meeting {meeting_id}: {response.error_details}")
                return {
                    "status": "failed",
                    "meeting_id": meeting_id,
                    "error": response.error_details
                }
                
            db.close()
            
        except Exception as e:
            logger.error(f"Auto-join failed for meeting {meeting_id}: {str(e)}")
            
            # Reset meeting status on error
            try:
                db = SessionLocal()
                meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
                if meeting:
                    meeting.status = "scheduled"
                    db.commit()
                db.close()
            except Exception as db_error:
                logger.error(f"Failed to reset meeting status: {str(db_error)}")
            
            return {
                "status": "failed",
                "meeting_id": meeting_id,
                "error": str(e)
            }
    
    # Run the async function
    return asyncio.run(_join_meeting_async())


@celery_app.task
def schedule_meeting_join(meeting_id: int, twin_id: int, meeting_url: str, platform: str, scheduled_time: datetime):
    """Schedule a digital twin to join a meeting at the specified time"""
    logger.info(f"Scheduling twin {twin_id} to join meeting {meeting_id} at {scheduled_time}")
    
    # This is a skeleton implementation
    # In a real implementation, you would:
    # 1. Schedule the task to run at the specified time
    # 2. Use a proper task scheduler like Celery beat
    
    return {
        "status": "scheduled",
        "meeting_id": meeting_id,
        "twin_id": twin_id,
        "scheduled_time": scheduled_time.isoformat()
    }


@celery_app.task
def join_meeting_task(meeting_id: int, twin_id: int, meeting_url: str, platform: str):
    """Task to join a meeting with digital twin using Recall AI"""
    logger.info(f"Joining meeting {meeting_id} with twin {twin_id} on platform {platform}")
    
    try:
        # Skeleton implementation for Recall AI integration
        recall_response = join_meeting_with_recall_ai(meeting_url, platform, twin_id)
        
        # Update meeting status in database
        # This would require database session management in Celery
        
        return {
            "status": "joined",
            "meeting_id": meeting_id,
            "twin_id": twin_id,
            "recall_bot_id": recall_response.get("bot_id"),
            "platform": platform
        }
        
    except Exception as e:
        logger.error(f"Failed to join meeting {meeting_id}: {str(e)}")
        return {
            "status": "failed",
            "meeting_id": meeting_id,
            "error": str(e)
        }


def join_meeting_with_recall_ai(meeting_url: str, platform: str, twin_id: int) -> dict:
    """
    Join meeting using Recall AI API
    This is a skeleton implementation
    """
    
    # Recall AI API endpoint (placeholder)
    recall_api_url = "https://api.recall.ai/api/v1/bot"
    
    # Prepare bot configuration
    bot_config = {
        "meeting_url": meeting_url,
        "bot_name": f"Digital Twin {twin_id}",
        "transcription_options": {
            "provider": "meeting_captions"
        },
        "chat": {
            "on_bot_join": {
                "send_to": "everyone",
                "message": "Digital twin has joined the meeting"
            }
        }
    }
    
    # Headers for Recall AI API
    headers = {
        "Authorization": f"Token {settings.RECALL_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # This is a skeleton - actual API call would be made here
        # response = requests.post(recall_api_url, json=bot_config, headers=headers)
        # response.raise_for_status()
        # return response.json()
        
        # Skeleton response
        return {
            "id": f"bot_{twin_id}_{datetime.now().timestamp()}",
            "status": "joining",
            "meeting_url": meeting_url,
            "bot_name": bot_config["bot_name"]
        }
        
    except Exception as e:
        logger.error(f"Recall AI API error: {str(e)}")
        raise


def get_meeting_recording(bot_id: str) -> Optional[dict]:
    """
    Get meeting recording from Recall AI
    This is a skeleton implementation
    """
    
    # Recall AI API endpoint for getting bot data
    recall_api_url = f"https://api.recall.ai/api/v1/bot/{bot_id}"
    
    headers = {
        "Authorization": f"Token {settings.RECALL_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # This is a skeleton - actual API call would be made here
        # response = requests.get(recall_api_url, headers=headers)
        # response.raise_for_status()
        # return response.json()
        
        # Skeleton response
        return {
            "id": bot_id,
            "status": "done",
            "video_url": f"https://storage.recall.ai/recordings/{bot_id}.mp4",
            "transcript": "This is a skeleton transcript",
            "summary": "This is a skeleton meeting summary"
        }
        
    except Exception as e:
        logger.error(f"Failed to get recording for bot {bot_id}: {str(e)}")
        return None


def stop_meeting_bot(bot_id: str) -> bool:
    """
    Stop a meeting bot
    This is a skeleton implementation
    """
    
    recall_api_url = f"https://api.recall.ai/api/v1/bot/{bot_id}/leave"
    
    headers = {
        "Authorization": f"Token {settings.RECALL_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # This is a skeleton - actual API call would be made here
        # response = requests.post(recall_api_url, headers=headers)
        # response.raise_for_status()
        
        logger.info(f"Bot {bot_id} stopped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to stop bot {bot_id}: {str(e)}")
        return False


@celery_app.task
def cleanup_old_meetings():
    """
    Clean up old completed meetings and update their status
    Runs daily to maintain database hygiene
    """
    logger.info("Running meeting cleanup task...")
    
    try:
        db = SessionLocal()
        
        # Update meetings that are past their end time but still marked as in_progress
        cutoff_time = datetime.utcnow() - timedelta(hours=6)  # 6 hours buffer
        
        old_meetings = db.query(Meeting).filter(
            and_(
                Meeting.status == "in_progress",
                Meeting.scheduled_time < cutoff_time
            )
        ).all()
        
        for meeting in old_meetings:
            # Calculate estimated end time
            estimated_end = meeting.scheduled_time + timedelta(minutes=meeting.duration_minutes)
            if datetime.utcnow() > estimated_end + timedelta(hours=1):  # 1 hour buffer
                meeting.status = "completed"
                logger.info(f"Marked meeting {meeting.id} as completed")
        
        db.commit()
        db.close()
        
        logger.info(f"Cleanup completed. Updated {len(old_meetings)} meetings.")
        
    except Exception as e:
        logger.error(f"Meeting cleanup error: {str(e)}")


def get_upcoming_auto_join_meetings(user_id: int = None) -> List[Meeting]:
    """
    Get meetings that are scheduled for auto-join in the next few hours
    Useful for dashboard/status displays
    """
    try:
        db = SessionLocal()
        
        now = datetime.utcnow()
        next_hour = now + timedelta(hours=2)
        
        query = db.query(Meeting).filter(
            and_(
                Meeting.auto_join == True,
                Meeting.status == "scheduled",
                Meeting.scheduled_time >= now,
                Meeting.scheduled_time <= next_hour,
                Meeting.digital_twin_id.isnot(None)
            )
        )
        
        if user_id:
            query = query.filter(Meeting.user_id == user_id)
        
        meetings = query.order_by(Meeting.scheduled_time).all()
        db.close()
        
        return meetings
        
    except Exception as e:
        logger.error(f"Error getting upcoming auto-join meetings: {str(e)}")
        return []


def force_join_meeting(meeting_id: int) -> dict:
    """
    Manually trigger auto-join for a specific meeting
    Useful for testing or manual intervention
    """
    try:
        db = SessionLocal()
        
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {"status": "failed", "error": "Meeting not found"}
        
        if not meeting.auto_join:
            return {"status": "failed", "error": "Auto-join not enabled for this meeting"}
        
        if not meeting.digital_twin_id:
            return {"status": "failed", "error": "No digital twin assigned to this meeting"}
        
        # Update status to prevent scheduler from picking it up
        meeting.status = "joining"
        db.commit()
        db.close()
        
        # Trigger the join task
        task = join_meeting_auto.delay(
            meeting.id,
            meeting.digital_twin_id,
            meeting.meeting_url,
            meeting.platform,
            meeting.user_id
        )
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "meeting_id": meeting_id
        }
        
    except Exception as e:
        logger.error(f"Force join failed for meeting {meeting_id}: {str(e)}")
        return {"status": "failed", "error": str(e)}