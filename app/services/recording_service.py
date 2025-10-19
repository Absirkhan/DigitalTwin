"""
Recording service for managing video recordings from Recall API
"""

import os
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.models.bot import Bot
from app.models.meeting import Meeting
from app.services.recall_service import recall_service
from app.schemas.meeting import RecordingResponse


class RecordingService:
    def __init__(self):
        self.recording_base_path = "recordings/generated"
        # Ensure recording directory exists
        os.makedirs(self.recording_base_path, exist_ok=True)

    async def update_bot_recording_status(self, bot_id: str, db: Session) -> Optional[Bot]:
        """
        Update bot recording status by fetching latest data from Recall API
        """
        try:
            # Fetch recording data from Recall API
            recording_response = await recall_service.get_bot_recordings(bot_id)
            
            # Find bot in database
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot:
                print(f"Bot with ID {bot_id} not found in database")
                return None
            
            if recording_response.success and recording_response.recordings:
                # Update bot with recording information
                latest_recording = recording_response.recordings[0]  # Get the most recent recording
                
                # Update recording status based on the API response
                api_status = latest_recording.status.get("code", "unknown")
                if api_status == "done":
                    bot.recording_status = "completed"
                elif api_status == "in_progress":
                    bot.recording_status = "recording"
                elif api_status == "failed":
                    bot.recording_status = "failed"
                else:
                    bot.recording_status = "pending"
                
                # Store full recording data
                bot.recording_data = {
                    "recordings": [recording.dict() for recording in recording_response.recordings],
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Store video download URL if available
                if recording_response.download_url:
                    bot.video_recording_url = recording_response.download_url
                
                # Set expiration time
                if latest_recording.expires_at:
                    bot.recording_expires_at = latest_recording.expires_at
                
                db.commit()
                print(f"Updated recording status for bot {bot_id}: {bot.recording_status}")
                return bot
            else:
                print(f"No recordings found or failed to fetch for bot {bot_id}")
                return bot
                
        except Exception as e:
            print(f"Error updating bot recording status: {str(e)}")
            db.rollback()
            return None

    async def download_and_store_recording(self, bot_id: str, db: Session) -> Optional[str]:
        """
        Download recording for a bot and store it locally
        """
        try:
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot:
                print(f"Bot with ID {bot_id} not found")
                return None
            
            if not bot.video_recording_url:
                print(f"No video recording URL found for bot {bot_id}")
                return None
            
            # Generate local file path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{bot_id}_{timestamp}.mp4"
            local_path = os.path.join(self.recording_base_path, filename)
            
            # Download the recording
            success = await recall_service.download_recording(bot.video_recording_url, local_path)
            
            if success:
                # Update bot with local file path
                bot.video_download_url = local_path
                db.commit()
                print(f"Recording downloaded and stored at: {local_path}")
                return local_path
            else:
                print(f"Failed to download recording for bot {bot_id}")
                return None
                
        except Exception as e:
            print(f"Error downloading recording: {str(e)}")
            return None

    async def check_and_update_expired_recordings(self, db: Session) -> List[str]:
        """
        Check for expired recording URLs and update their status
        """
        try:
            # Find bots with recording URLs that might be expired
            current_time = datetime.utcnow()
            expired_bots = db.query(Bot).filter(
                and_(
                    Bot.recording_expires_at.isnot(None),
                    Bot.recording_expires_at < current_time,
                    Bot.video_recording_url.isnot(None)
                )
            ).all()
            
            expired_bot_ids = []
            for bot in expired_bots:
                # Clear expired URL
                bot.video_recording_url = None
                bot.recording_status = "expired"
                expired_bot_ids.append(bot.bot_id)
                print(f"Marked recording as expired for bot {bot.bot_id}")
            
            if expired_bot_ids:
                db.commit()
            
            return expired_bot_ids
            
        except Exception as e:
            print(f"Error checking expired recordings: {str(e)}")
            db.rollback()
            return []

    async def get_recording_status(self, bot_id: str, db: Session) -> dict:
        """
        Get recording status and information for a bot
        """
        try:
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot:
                return {"error": "Bot not found"}
            
            return {
                "bot_id": bot.bot_id,
                "recording_status": bot.recording_status,
                "video_recording_url": bot.video_recording_url,
                "video_download_url": bot.video_download_url,
                "recording_expires_at": bot.recording_expires_at.isoformat() if bot.recording_expires_at else None,
                "recording_data": bot.recording_data,
                "has_local_file": bool(bot.video_download_url and os.path.exists(bot.video_download_url))
            }
            
        except Exception as e:
            return {"error": f"Error getting recording status: {str(e)}"}

    async def process_completed_recording(self, bot_id: str, db: Session) -> bool:
        """
        Process a completed recording (update status and optionally download)
        """
        try:
            # Update recording status from API
            bot = await self.update_bot_recording_status(bot_id, db)
            if not bot:
                return False
            
            # If recording is completed and we have a URL, download it
            if bot.recording_status == "completed" and bot.video_recording_url:
                local_path = await self.download_and_store_recording(bot_id, db)
                return bool(local_path)
            
            return True
            
        except Exception as e:
            print(f"Error processing completed recording: {str(e)}")
            return False

    def get_local_recording_path(self, bot_id: str, db: Session) -> Optional[str]:
        """
        Get the local file path for a bot's recording if it exists
        """
        try:
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if bot and bot.video_download_url and os.path.exists(bot.video_download_url):
                return bot.video_download_url
            return None
        except Exception as e:
            print(f"Error getting local recording path: {str(e)}")
            return None


# Global service instance
recording_service = RecordingService()