"""
Simple auto-join scheduler without Redis/Celery
This is a lightweight alternative for testing auto-join functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.models.bot import Bot
from app.models.user import User
from app.schemas.meeting import MeetingJoinRequest
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pakistan/Karachi timezone (UTC+5)
PAKISTAN_TZ = timezone(timedelta(hours=5))

class SimpleAutoJoinScheduler:
    """Simple scheduler that runs in a loop without Celery"""
    
    def __init__(self):
        self.running = False
        
    async def check_and_join_meetings(self):
        """Check for meetings that need auto-joining and join them (Pakistan time logic)"""
        try:
            db = SessionLocal()
            # Get current Pakistan time (naive)
            pakistan_now = datetime.now().replace(second=0, microsecond=0)
            join_window_start = pakistan_now
            join_window_end = pakistan_now + timedelta(minutes=settings.AUTO_JOIN_ADVANCE_MINUTES)

            logger.info(f"🇵🇰 Pakistan time: {pakistan_now.strftime('%Y-%m-%d %H:%M:%S')} (PKT)")
            logger.info(f"🔍 Checking for meetings between {join_window_start.strftime('%H:%M:%S')} and {join_window_end.strftime('%H:%M:%S')} PKT")

            # Debug: Show all auto-join enabled meetings
            all_auto_join_meetings = db.query(Meeting).filter(
                Meeting.auto_join == True
            ).all()

            logger.info(f"📊 Total auto-join enabled meetings in DB: {len(all_auto_join_meetings)}")
            for meeting in all_auto_join_meetings:
                # Treat scheduled_time as Pakistan time (naive)
                logger.info(f"  📅 Meeting {meeting.id}: '{meeting.title}' at {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} PKT (Pakistan time)")
                logger.info(f"      Status: {meeting.status}, Digital Twin ID: {meeting.digital_twin_id}")

            # Find meetings that need auto-joining (Pakistan time logic)
            meetings_to_join = db.query(Meeting).filter(
                and_(
                    Meeting.auto_join == True,
                    Meeting.status == "scheduled",
                    Meeting.scheduled_time >= join_window_start,
                    Meeting.scheduled_time <= join_window_end,
                    Meeting.digital_twin_id.isnot(None)
                )
            ).all()

            logger.info(f"🎯 Found {len(meetings_to_join)} meetings ready to auto-join")
            for meeting in meetings_to_join:
                try:
                    await self.join_meeting(meeting, db)
                except Exception as e:
                    logger.error(f"Failed to auto-join meeting {meeting.id}: {str(e)}")
            db.close()
        except Exception as e:
            logger.error(f"Auto-join check error: {str(e)}")
    
    async def join_meeting(self, meeting: Meeting, db: Session):
        """Join a single meeting using the FastAPI endpoint"""
        try:
            # Update meeting status to prevent duplicate joins
            meeting.status = "joining"
            db.commit()
            
            # Get user details for bot naming and profile picture
            user = db.query(User).filter(User.id == meeting.user_id).first()
            # Use custom bot name if set, otherwise use default
            bot_name = user.bot_name if user and user.bot_name else "Digital Twin Bot"
            profile_picture = user.profile_picture if user and user.profile_picture else None
            
            # Create the join request payload (matching manual endpoint structure)
            join_request_data = {
                "meeting_url": meeting.meeting_url,
                "bot_name": bot_name,
                "enable_realtime_processing": False,
                "recording_config": {}  # Add this to match manual endpoint structure
            }
            
            # Add profile picture if available
            if profile_picture:
                join_request_data["profile_picture"] = profile_picture
            
            logger.info(f"Attempting to join meeting {meeting.id}: {meeting.title}")
            
            # Call the recall service directly for auto-join (internal process)
            try:
                logger.info(f"🔌 Calling Recall service for meeting URL: {meeting.meeting_url}")
                
                # Create the join request with user's profile settings
                join_request = MeetingJoinRequest(
                    meeting_url=meeting.meeting_url,
                    bot_name=bot_name,
                    profile_picture=profile_picture,
                    enable_realtime_processing=False,
                    recording_config={}
                )
                
                # Import and use recall service
                from app.services.recall_service import recall_service
                response = await recall_service.join_meeting(join_request)
                
                logger.info(f"📡 Recall service response: success={response.success}")
                
                # Check if response is successful
                if response.success and response.bot_id:
                    # Update meeting status
                    meeting.status = "in_progress"
                    
                    # Create or update bot record with correct user_id
                    existing_bot = db.query(Bot).filter(Bot.bot_id == response.bot_id).first()
                    if not existing_bot:
                        new_bot = Bot(
                            bot_id=response.bot_id,
                            user_id=meeting.user_id,  # Use meeting's user_id (correct user)
                            bot_name=bot_name,
                            platform=meeting.platform,
                            meeting_id=meeting.id
                        )
                        db.add(new_bot)
                    else:
                        existing_bot.meeting_id = meeting.id
                        existing_bot.platform = meeting.platform
                        existing_bot.user_id = meeting.user_id  # Ensure correct user_id
                    
                    db.commit()
                    logger.info(f"✅ Successfully auto-joined meeting {meeting.id} with bot {response.bot_id}")
                    
                else:
                    # Handle failed response
                    error_msg = response.message if hasattr(response, 'message') else 'Unknown error'
                    
                    # Update meeting status back to scheduled if join failed
                    meeting.status = "scheduled"
                    db.commit()
                    
                    logger.error(f"❌ Failed to auto-join meeting {meeting.id}: {error_msg}")
                    
            except Exception as api_error:
                # Handle API call exceptions
                meeting.status = "scheduled"
                db.commit()
                logger.error(f"❌ Recall service error for meeting {meeting.id}: {str(api_error)}")
                
                # Log more details about the error
                if "validation" in str(api_error).lower():
                    logger.error(f"   Validation error - check Recall API credentials and meeting URL format")
                elif "connection" in str(api_error).lower():
                    logger.error(f"   Connection error - check internet connection and Recall API status")
                else:
                    logger.error(f"   Unexpected error: {type(api_error).__name__}")
            
        except Exception as e:
            logger.error(f"❌ Auto-join failed for meeting {meeting.id}: {str(e)}")
            
            # Reset meeting status on error
            meeting.status = "scheduled"
            db.commit()
    
    async def run(self):
        """Main scheduler loop"""
        self.running = True
        pakistan_now = datetime.now(PAKISTAN_TZ)
        logger.info("🤖 Simple Auto-Join Scheduler Started")
        logger.info(f"🇵🇰 Pakistan Time: {pakistan_now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+5)")
        logger.info(f"⏰ Checking every {settings.AUTO_JOIN_CHECK_INTERVAL} seconds")
        logger.info(f"🎯 Joining meetings {settings.AUTO_JOIN_ADVANCE_MINUTES} minutes before start time")
        
        try:
            while self.running:
                await self.check_and_join_meetings()
                await asyncio.sleep(settings.AUTO_JOIN_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")
        except Exception as e:
            logger.error(f"💥 Scheduler error: {str(e)}")
        finally:
            self.running = False
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False

async def main():
    """Run the simple auto-join scheduler"""
    scheduler = SimpleAutoJoinScheduler()
    
    try:
        await scheduler.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopping auto-join scheduler...")
        scheduler.stop()

if __name__ == "__main__":
    print("🚀 Starting Simple Auto-Join Scheduler (Redis-free version)")
    print("📝 This version doesn't require Redis/Celery")
    print("⚠️  For production, use the full Celery version with Redis")
    print("\nPress Ctrl+C to stop\n")
    
    asyncio.run(main())