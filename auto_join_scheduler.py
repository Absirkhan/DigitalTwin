"""
Simple Auto-Join Scheduler for Calendar Meetings
Automatically joins meetings that are detected from calendar webhooks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoJoinScheduler:
    """Simple scheduler that automatically joins calendar meetings"""
    
    def __init__(self):
        self.running = False
        
    async def start(self):
        """Start the auto-join scheduler"""
        self.running = True
        logger.info("🤖 Auto-Join Scheduler started!")
        
        while self.running:
            try:
                await self.check_and_join_meetings()
                # Check every 30 seconds
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"❌ Error in scheduler: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("🛑 Auto-Join Scheduler stopped")
    
    async def check_and_join_meetings(self):
        """Check for meetings that should be joined now"""
        from app.core.database import get_db
        from app.models.meeting import Meeting
        from app.services.recall_service import recall_service
        from app.schemas.meeting import MeetingJoinRequest
        
        db = next(get_db())
        
        try:
            # Get current time
            now = datetime.utcnow()
            
            # Find meetings that should be joined:
            # 1. Scheduled status
            # 2. Start time is within next 2 minutes
            # 3. Has meeting URL
            # 4. From calendar (has calendar_event_id)
            upcoming_meetings = db.query(Meeting).filter(
                Meeting.status == "scheduled",
                Meeting.scheduled_time <= now + timedelta(minutes=2),
                Meeting.scheduled_time >= now - timedelta(minutes=1),  # Don't join late
                Meeting.meeting_url.isnot(None),
                Meeting.calendar_event_id.isnot(None)  # Only calendar meetings
            ).all()
            
            if upcoming_meetings:
                logger.info(f"📅 Found {len(upcoming_meetings)} meetings to join")
            
            for meeting in upcoming_meetings:
                await self.join_meeting(meeting, db)
                
        except Exception as e:
            logger.error(f"❌ Error checking meetings: {e}")
        finally:
            db.close()
    
    async def join_meeting(self, meeting: Meeting, db: Session):
        """Join a single meeting using the Recall API"""
        try:
            logger.info(f"🚀 Auto-joining meeting: {meeting.title} ({meeting.meeting_url})")
            
            # Get user for bot name
            user = meeting.user
            bot_name = user.bot_name or f"{user.full_name or 'Digital'} Twin" or "Digital Twin Bot"
            
            # Create join request
            join_request = MeetingJoinRequest(
                meeting_url=meeting.meeting_url,
                bot_name=bot_name,
                enable_video_recording=True,  # Enable recording by default
                enable_realtime_processing=False
            )
            
            # Join the meeting
            response = await recall_service.join_meeting(join_request)
            
            if response.success and response.bot_id:
                # Update meeting status
                meeting.status = "in_progress"
                
                # Create bot record
                from app.models.bot import Bot
                existing_bot = db.query(Bot).filter(Bot.bot_id == response.bot_id).first()
                if not existing_bot:
                    new_bot = Bot(
                        bot_id=response.bot_id,
                        user_id=meeting.user_id,
                        bot_name=bot_name,
                        platform=meeting.platform,
                        meeting_id=meeting.id,
                        recording_status="pending"
                    )
                    db.add(new_bot)
                
                db.commit()
                logger.info(f"✅ Successfully auto-joined meeting {meeting.id} with bot {response.bot_id}")
                
            else:
                error_msg = response.message if hasattr(response, 'message') else 'Unknown error'
                logger.error(f"❌ Failed to auto-join meeting {meeting.id}: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Error auto-joining meeting {meeting.id}: {str(e)}")


# Global scheduler instance
auto_join_scheduler = AutoJoinScheduler()


async def main():
    """Main function to run the scheduler"""
    try:
        await auto_join_scheduler.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
        auto_join_scheduler.stop()


if __name__ == "__main__":
    print("🤖 Starting Digital Twin Auto-Join Scheduler...")
    print("📅 Will automatically join calendar meetings with video recording")
    print("🔄 Checking every 30 seconds for meetings to join")
    print("⏰ Joins meetings up to 2 minutes after start time")
    print("Press Ctrl+C to stop")
    
    asyncio.run(main())