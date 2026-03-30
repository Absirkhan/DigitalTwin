"""
Meeting Status Monitor Service

Periodically polls Recall.ai to check bot status and automatically updates
meeting status to "completed" when the host ends the meeting.

Why this is needed:
- Recall.ai does NOT send bot.status_change events via webhooks
- We only get transcript.data events in real-time
- Must poll the Recall API to detect when meetings end
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.meeting import Meeting
from app.models.bot import Bot
from app.models.user import User
from app.services.recall_service import recall_service

logger = logging.getLogger(__name__)


class MeetingStatusMonitor:
    """
    Background service that monitors ongoing meetings and updates their status
    when the Recall.ai bot reports completion.
    """

    def __init__(self, poll_interval: int = 30):
        """
        Initialize the meeting status monitor.

        Args:
            poll_interval: How often to check bot statuses (in seconds). Default: 30s
        """
        self.poll_interval = poll_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background monitoring task."""
        if self.running:
            logger.warning("Meeting status monitor is already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"✅ Meeting status monitor started (poll interval: {self.poll_interval}s)")

    async def stop(self):
        """Stop the background monitoring task."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("⛔ Meeting status monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - runs continuously in the background."""
        while self.running:
            try:
                await self._check_all_active_meetings()
            except Exception as e:
                logger.error(f"❌ Error in meeting status monitor loop: {e}", exc_info=True)

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    async def _check_all_active_meetings(self):
        """Check all meetings that are currently in progress."""
        db = AsyncSessionLocal()

        try:
            # Find all meetings in 'in_progress' status
            result = await db.execute(
                select(Meeting).filter(
                    Meeting.status == "in_progress"
                )
            )
            active_meetings = result.scalars().all()

            if not active_meetings:
                logger.debug("No active meetings to monitor")
                return

            logger.info(f"🔍 Checking {len(active_meetings)} active meeting(s)")

            # Check each meeting
            for meeting in active_meetings:
                await self._check_meeting_status(meeting, db)

            await db.commit()

        except Exception as e:
            logger.error(f"❌ Error checking active meetings: {e}", exc_info=True)
            await db.rollback()

        finally:
            await db.close()

    async def _check_meeting_status(self, meeting: Meeting, db: AsyncSession):
        """
        Check the status of a specific meeting by querying its bot.

        Args:
            meeting: The meeting to check
            db: Database session
        """
        try:
            # Find the bot associated with this meeting
            result = await db.execute(
                select(Bot).filter(Bot.meeting_id == meeting.id)
            )
            bot = result.scalar_one_or_none()

            if not bot or not bot.bot_id:
                logger.warning(f"⚠️ Meeting {meeting.id} has no associated bot")
                return

            # Query Recall.ai for current bot status
            bot_data = await recall_service.get_bot_status(bot.bot_id)

            if "error" in bot_data:
                logger.error(f"❌ Failed to get bot status for {bot.bot_id}: {bot_data.get('error')}")
                return

            # Extract bot status from Recall.ai response
            # Possible statuses: "ready", "joining", "in_call", "done", "failed", "fatal"
            # The API returns status_changes as a LIST of status change events
            # Get the latest status from the list, or fall back to the 'status' field
            bot_status = bot_data.get("status")  # Primary: direct status field

            # If status_changes is present and is a list, get the latest status code
            status_changes = bot_data.get("status_changes")
            if isinstance(status_changes, list) and status_changes:
                # Get the most recent status change (last item in the list)
                latest_change = status_changes[-1]
                if isinstance(latest_change, dict) and "code" in latest_change:
                    bot_status = latest_change["code"]

            logger.debug(f"Bot {bot.bot_id} status: {bot_status}")

            # Update bot recording status
            bot.recording_status = bot_status
            bot.updated_at = datetime.utcnow()

            # Check if meeting should be marked as completed
            if bot_status in ["done", "failed", "fatal", "analysis_done"]:
                old_status = meeting.status
                meeting.status = "completed"

                # Set end_time if not already set
                if not meeting.end_time:
                    meeting.end_time = datetime.utcnow()

                logger.info(
                    f"✅ Meeting {meeting.id} ({meeting.title or 'Untitled'}) "
                    f"status updated: {old_status} → completed (bot status: {bot_status})"
                )

                # Also mark bot recording as completed
                if bot_status == "done":
                    bot.recording_status = "completed"

                    # ===== AUTO-STORE TRANSCRIPT IN RAG =====
                    # Automatically store meeting transcript in RAG for future context retrieval
                    try:
                        # Get user information for name detection
                        user_result = await db.execute(
                            select(User).filter(User.id == meeting.user_id)
                        )
                        user = user_result.scalar_one_or_none()

                        if user:
                            # Import RAG service
                            from app.services.rag_service import rag_service

                            # Determine user's name in transcript
                            user_name = user.full_name or user.email.split('@')[0]
                            bot_name = user.bot_name or f"{user_name}'s Bot"

                            # Store transcript in RAG
                            logger.info(f"📝 Storing transcript in RAG for meeting {meeting.id}...")

                            result = await rag_service.store_meeting_transcript(
                                user_id=str(meeting.user_id),
                                bot_id=bot.bot_id,
                                user_name=user_name,
                                bot_name=bot_name
                            )

                            if result.get('success'):
                                logger.info(
                                    f"✅ Stored {result['total_exchanges_stored']} transcript "
                                    f"exchanges in RAG for meeting {meeting.id} "
                                    f"({len(result['speakers'])} speakers: {', '.join(result['speakers'])})"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ Failed to store transcript in RAG for meeting {meeting.id}: "
                                    f"{result.get('error', 'Unknown error')}"
                                )
                        else:
                            logger.warning(f"⚠️ User {meeting.user_id} not found for RAG storage")

                    except Exception as rag_error:
                        # Don't fail the status update if RAG storage fails
                        logger.error(
                            f"❌ Error storing transcript in RAG for meeting {meeting.id}: {rag_error}",
                            exc_info=True
                        )

        except Exception as e:
            logger.error(f"❌ Error checking meeting {meeting.id} status: {e}", exc_info=True)

    async def check_meeting_now(self, meeting_id: int) -> dict:
        """
        Manually check a specific meeting's status immediately.

        Args:
            meeting_id: ID of the meeting to check

        Returns:
            dict with status update information
        """
        db = AsyncSessionLocal()

        try:
            result = await db.execute(
                select(Meeting).filter(Meeting.id == meeting_id)
            )
            meeting = result.scalar_one_or_none()

            if not meeting:
                return {"error": "Meeting not found"}

            old_status = meeting.status

            await self._check_meeting_status(meeting, db)
            await db.commit()

            return {
                "success": True,
                "meeting_id": meeting_id,
                "old_status": old_status,
                "new_status": meeting.status,
                "updated": old_status != meeting.status
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error checking meeting {meeting_id}: {e}", exc_info=True)
            return {"error": str(e)}

        finally:
            await db.close()


# Global instance
_monitor: Optional[MeetingStatusMonitor] = None


def get_meeting_status_monitor(poll_interval: int = 30) -> MeetingStatusMonitor:
    """
    Get or create the global meeting status monitor instance.

    Args:
        poll_interval: Polling interval in seconds (default: 30)

    Returns:
        MeetingStatusMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = MeetingStatusMonitor(poll_interval=poll_interval)
    return _monitor


async def start_meeting_status_monitor(poll_interval: int = 30):
    """
    Start the global meeting status monitor.

    Args:
        poll_interval: Polling interval in seconds (default: 30)
    """
    monitor = get_meeting_status_monitor(poll_interval)
    await monitor.start()


async def stop_meeting_status_monitor():
    """Stop the global meeting status monitor."""
    global _monitor
    if _monitor:
        await _monitor.stop()
