"""
Real-Time Transcript API Endpoints

Two main endpoints:
1. WebSocket endpoint for frontend clients to connect and receive live transcripts
2. HTTP webhook endpoint for Recall.ai to push transcript chunks

Ultra-low latency design:
- No database writes in hot path (async background task)
- Direct Redis pub/sub (no queuing)
- Parallel message broadcasting
"""

import logging
import asyncio
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    status,
    Request,
    Header
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_async_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.bot import Bot
from app.schemas.realtime import (
    RecallWebhookEvent,
    RecallTranscriptData,
    RealtimeTranscriptChunk,
    WebSocketConnectionInfo
)
from app.services.websocket_manager import get_websocket_manager
from app.services.redis_pubsub import get_redis_pubsub
from app.services.auth import get_current_user_from_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Get service instances
ws_manager = get_websocket_manager()
redis_pubsub = get_redis_pubsub()


# ==================== WebSocket Endpoint for Frontend Clients ====================

@router.websocket("/ws/transcript/{meeting_id}")
async def websocket_transcript_stream(
    websocket: WebSocket,
    meeting_id: int,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming real-time transcripts to frontend clients.

    **Connection URL:**
    ```
    ws://localhost:8000/api/v1/realtime/ws/transcript/{meeting_id}?token={jwt_token}
    ```

    **Authentication:**
    - JWT token passed as query parameter
    - Validates user has access to the meeting

    **Message Format (sent to client):**
    ```json
    {
        "type": "transcript_chunk",
        "meeting_id": 123,
        "speaker": "John Doe",
        "text": "Hello everyone",
        "timestamp": 1234567890.123,
        "confidence": 0.95,
        "is_final": true
    }
    ```

    **Performance:**
    - Direct Redis subscription (no polling)
    - Messages forwarded immediately upon receipt
    - Parallel broadcast to all connected clients
    """

    user_id = None
    db = None

    try:
        # ===== PHASE 0: Accept WebSocket Connection =====
        # MUST accept before doing anything else with the WebSocket
        await websocket.accept()
        logger.info(f"🔌 WebSocket connection accepted for meeting {meeting_id}")

        # ===== PHASE 1: Create Database Session =====
        # Manually create session for WebSocket (Depends doesn't work well with WebSockets)
        from app.core.database import AsyncSessionLocal
        db = AsyncSessionLocal()

        # ===== PHASE 2: Authenticate User =====
        if not token:
            logger.error(f"❌ WebSocket missing token for meeting {meeting_id}")
            await websocket.close(code=4001, reason="Missing authentication token")
            return

        try:
            # Validate JWT token
            user: User = await get_current_user_from_token(token, db)
            user_id = user.id

            logger.info(
                f"🔐 WebSocket auth successful: user={user.email}, meeting={meeting_id}"
            )

        except Exception as e:
            logger.error(f"❌ WebSocket authentication failed: {e}", exc_info=True)
            await websocket.close(code=4001, reason="Invalid authentication token")
            return

        # ===== PHASE 3: Verify Access to Meeting =====
        # Check if meeting exists and belongs to user
        from sqlalchemy import select
        result = await db.execute(
            select(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            )
        )
        meeting = result.scalar_one_or_none()

        if not meeting:
            logger.warning(
                f"⚠️ User {user_id} attempted to access unauthorized meeting {meeting_id}"
            )
            await websocket.close(code=4003, reason="Meeting not found or access denied")
            return

        # ===== PHASE 4: Register with WebSocket Manager =====
        # Note: ws_manager.connect does NOT call websocket.accept() - already done above
        await ws_manager.connect(websocket, meeting_id, user_id)

        logger.info(
            f"✅ Real-time transcript stream started: "
            f"meeting={meeting_id}, user={user.email}, status={meeting.status}"
        )

        # ===== PHASE 4: Keep Connection Alive =====
        # Listen for client messages (mostly for heartbeat/ping)
        try:
            while True:
                # Wait for client messages (used for keepalive)
                data = await websocket.receive_text()

                # Handle client commands (optional)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info(f"🔌 Client disconnected from meeting {meeting_id}")

        except Exception as e:
            logger.error(f"❌ WebSocket error in message loop: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ Unexpected error in WebSocket handler: {e}", exc_info=True)
        # Try to send error to client if possible
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

    finally:
        # ===== PHASE 5: Cleanup =====
        if user_id:
            await ws_manager.disconnect(websocket, meeting_id)
            logger.info(f"🧹 WebSocket cleanup complete for meeting {meeting_id}")

        # Close database session
        if db:
            await db.close()


# ==================== HTTP Webhook Endpoint for Recall.ai ====================

@router.post("/webhook/recall")
async def receive_recall_webhook(
    request: Request,
    x_recall_signature: Optional[str] = Header(None)
):
    """
    Webhook endpoint for receiving real-time transcript chunks from Recall.ai.

    **Called by:** Recall.ai when bot is configured with realtime_endpoints

    **Request Payload (from Recall.ai):**
    ```json
    {
        "event_type": "transcript.data",
        "bot_id": "550e8400-e29b-41d4-a716-446655440000",
        "data": {
            "speaker": "John Doe",
            "words": [
                {"text": "Hello", "start": 0.0, "end": 0.5},
                {"text": "everyone", "start": 0.5, "end": 1.0}
            ],
            "is_final": true,
            "timestamp": 1234567890.123
        }
    }
    ```

    **Processing Flow (ULTRA LOW LATENCY):**
    1. Parse incoming webhook payload (< 1ms)
    2. Look up meeting by bot_id (DB index lookup, < 5ms)
    3. Publish to Redis pub/sub (< 1ms)
    4. Return 200 OK immediately (< 10ms total)
    5. Redis forwards to all WebSocket clients (< 5ms)

    **Total latency: < 20ms from Recall.ai → Frontend**
    """

    # Create manual database session (no auto-transaction)
    from app.core.database import AsyncSessionLocal
    db = AsyncSessionLocal()

    try:
        # ===== PHASE 1: Parse Webhook Payload =====
        payload = await request.json()

        # Extract event type - ACTUAL Recall.ai structure uses "event" not "event_type"
        event_type = payload.get("event") or payload.get("event_type")

        # Bot ID is nested in data.bot.id
        bot_id = payload.get("bot_id")  # Old structure
        if not bot_id:
            # New structure: data.bot.id
            bot_id = payload.get("data", {}).get("bot", {}).get("id")

        logger.info(
            f"📥 Received Recall webhook: event={event_type}, bot={bot_id}"
        )

        # ===== Handle Different Event Types =====

        # BOT STATUS EVENTS - Update meeting status when bot joins/leaves
        # Listen for all bot status events including done/failed
        if event_type in ["bot.status_change", "bot.joined", "bot.ready", "bot.done", "bot.failed", "bot.left"]:
            await _handle_bot_status_change(bot_id, payload, db)
            return {"status": "processed", "event_type": event_type}

        # Only process transcript events below this point
        if event_type != "transcript.data":
            logger.info(f"ℹ️ Ignoring event: {event_type}")
            return {"status": "ignored", "event_type": event_type}

        # ===== PHASE 2: Look Up Meeting by Bot ID =====
        from sqlalchemy import select
        result = await db.execute(
            select(Bot).filter(Bot.bot_id == bot_id)
        )
        bot = result.scalar_one_or_none()

        if not bot or not bot.meeting_id:
            logger.warning(f"⚠️ Bot not found or not associated with meeting: {bot_id}")
            return {"status": "error", "error": "Bot not found"}

        meeting_id = bot.meeting_id

        # ===== PHASE 3: Parse Transcript Data from ACTUAL Recall.ai Structure =====
        # Actual structure: payload.data.data.words, payload.data.data.participant
        try:
            transcript_data = payload.get("data", {}).get("data", {})
            words_data = transcript_data.get("words", [])
            participant_data = transcript_data.get("participant", {})

            # Extract participant name
            speaker_name = participant_data.get("name", "Unknown Speaker")

            # Combine words into text
            text = " ".join([word.get("text", "") for word in words_data])

            # Get timestamp (use absolute timestamp from first word)
            timestamp = None
            if words_data:
                first_word = words_data[0]
                timestamp_data = first_word.get("start_timestamp", {})
                # Parse ISO timestamp to float
                from datetime import datetime
                absolute_ts = timestamp_data.get("absolute")
                if absolute_ts:
                    try:
                        dt = datetime.fromisoformat(absolute_ts.replace("Z", "+00:00"))
                        timestamp = dt.timestamp()
                    except:
                        timestamp = asyncio.get_event_loop().time()
                else:
                    timestamp = asyncio.get_event_loop().time()
            else:
                timestamp = asyncio.get_event_loop().time()

            # Create transcript chunk
            chunk = RealtimeTranscriptChunk(
                meeting_id=meeting_id,
                speaker=speaker_name,
                text=text,
                timestamp=timestamp,
                confidence=None,  # Recall.ai doesn't provide confidence in this format
                is_final=True  # Assume final for now
            )

            # ===== PHASE 4: Publish to Redis (Fire-and-Forget) =====
            # This is THE critical performance path - must be fast!
            await redis_pubsub.publish_transcript_chunk(
                meeting_id=meeting_id,
                chunk_data=chunk.model_dump()
            )

            logger.debug(
                f"📤 Published transcript chunk: meeting={meeting_id}, "
                f"speaker={chunk.speaker}, text='{text[:50]}...'"
            )

            # ===== PHASE 4.5: Check if Bot Should Respond (Bot Speaking) =====
            # Do NOT block webhook response - this is a fire-and-forget background task
            await _check_bot_speaking(bot, meeting_id, chunk, db)

            # ===== PHASE 5: Background Task - Store in Database =====
            # Do NOT block webhook response for database writes
            # Note: Create task without passing db session - it will create its own
            asyncio.create_task(_store_transcript_chunk(meeting_id, chunk))

            # ===== PHASE 6: Return Success Immediately =====
            return {
                "status": "success",
                "meeting_id": meeting_id,
                "chunk_length": len(text)
            }

        except Exception as e:
            logger.error(f"❌ Error parsing transcript data: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    except Exception as e:
        logger.error(f"❌ Error processing Recall webhook: {e}", exc_info=True)
        # Still return 200 to prevent Recall.ai from retrying
        return {"status": "error", "error": str(e)}

    finally:
        # Always close the database session
        await db.close()


async def _handle_bot_status_change(bot_id: str, payload: dict, db: AsyncSession):
    """
    Handle bot status change events from Recall.ai.
    Updates meeting status when bot joins/leaves.
    """
    try:
        from sqlalchemy import select
        from datetime import datetime

        # Find bot in database
        result = await db.execute(
            select(Bot).filter(Bot.bot_id == bot_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            logger.warning(f"⚠️ Bot {bot_id} not found in database")
            return

        # Extract status from payload
        bot_status = payload.get("data", {}).get("status") or payload.get("status")

        # Update bot status
        if bot_status:
            bot.recording_status = bot_status
            bot.updated_at = datetime.utcnow()

        # If bot is linked to a meeting, update meeting status
        if bot.meeting_id:
            result = await db.execute(
                select(Meeting).filter(Meeting.id == bot.meeting_id)
            )
            meeting = result.scalar_one_or_none()

            if meeting:
                # Bot joined/ready → Meeting is in_progress
                if bot_status in ["in_call", "in_waiting_room", "recording", "in_call_not_recording", "in_call_recording"]:
                    meeting.status = "in_progress"
                    # Set start_time if not already set
                    if not meeting.start_time:
                        meeting.start_time = datetime.utcnow()
                    logger.info(f"✅ Meeting {meeting.id} status → in_progress")

                # Bot left/done → Meeting is completed
                elif bot_status in ["done", "failed", "fatal", "analysis_done"]:
                    old_status = meeting.status
                    meeting.status = "completed"
                    # Set end_time when meeting completes
                    if not meeting.end_time:
                        meeting.end_time = datetime.utcnow()
                    logger.info(f"✅ Meeting {meeting.id} status: {old_status} → completed")

                meeting.updated_at = datetime.utcnow()

        await db.commit()

    except Exception as e:
        logger.error(f"❌ Error handling bot status change: {e}", exc_info=True)
        await db.rollback()


async def _check_bot_speaking(bot: Bot, meeting_id: int, chunk: RealtimeTranscriptChunk, db: AsyncSession):
    """
    Check if bot should respond to this transcript chunk.

    This is called after publishing to Redis, as a non-blocking check.
    If bot should respond, queues a background task for response generation.

    Args:
        bot: Bot instance
        meeting_id: ID of the meeting
        chunk: Transcript chunk received
        db: Database session
    """
    try:
        print(f"\n🔍 _check_bot_speaking CALLED: meeting={meeting_id}, text='{chunk.text}'")

        # Import here to avoid circular dependencies
        from app.services.optimized_bot_response_pipeline import check_and_respond_if_addressed
        from sqlalchemy import select

        # Get meeting to check bot speaking settings
        result = await db.execute(
            select(Meeting).filter(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()

        if not meeting:
            print(f"❌ EARLY RETURN: Meeting {meeting_id} not found")
            return

        # Check if bot speaking is enabled globally for user
        result = await db.execute(
            select(User).filter(User.id == bot.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ EARLY RETURN: User {bot.user_id} not found")
            return

        if not user.enable_bot_speaking:
            print(f"❌ EARLY RETURN: Bot speaking disabled globally for user {bot.user_id} (enable_bot_speaking={user.enable_bot_speaking})")
            return

        # Check if bot speaking is enabled for this meeting
        if not meeting.bot_response_enabled:
            print(f"❌ EARLY RETURN: Bot speaking disabled for meeting {meeting_id} (bot_response_enabled={meeting.bot_response_enabled})")
            return

        # Check if meeting is in progress
        if meeting.status != "in_progress":
            print(f"❌ EARLY RETURN: Meeting {meeting_id} not in progress (status={meeting.status})")
            return

        # Get bot name (from meeting or user)
        bot_name = meeting.bot_name or user.bot_name or "Digital Twin"

        print(f"✅ ALL CHECKS PASSED! bot_name='{bot_name}', speaker='{chunk.speaker}'")

        logger.info(
            f"🔍 Bot speaking check: meeting={meeting_id}, bot_name='{bot_name}', "
            f"speaker='{chunk.speaker}', text='{chunk.text[:80]}'"
        )

        # Check and respond if addressed (non-blocking background task)
        await check_and_respond_if_addressed(
            meeting_id=meeting_id,
            bot_id=bot.bot_id,
            user_id=bot.user_id,
            chunk_text=chunk.text,
            chunk_speaker=chunk.speaker,
            bot_name=bot_name,
            response_style=meeting.bot_response_style,
            max_responses=meeting.bot_max_responses
        )

    except Exception as e:
        # Don't fail the webhook if bot speaking check fails
        print(f"❌ EXCEPTION in _check_bot_speaking: {e}")
        logger.error(f"❌ Error in bot speaking check: {e}", exc_info=True)


async def _store_transcript_chunk(
    meeting_id: int,
    chunk: RealtimeTranscriptChunk
):
    """
    Background task to store transcript chunks in database.

    **Not blocking the webhook response** - runs async after Redis publish.

    This allows for:
    - Historical replay of transcripts
    - Search and indexing
    - AI summarization input
    """
    # Create a fresh database session for this background task
    from app.core.database import AsyncSessionLocal
    db = AsyncSessionLocal()

    try:
        from sqlalchemy import select
        result = await db.execute(
            select(Meeting).filter(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()

        if not meeting:
            logger.warning(f"Meeting {meeting_id} not found for chunk storage")
            return

        # Append to existing transcript (simple approach)
        # Format: [HH:MM:SS] Speaker: Text
        from datetime import datetime
        timestamp_str = datetime.fromtimestamp(chunk.timestamp).strftime("%H:%M:%S")
        chunk_text = f"[{timestamp_str}] {chunk.speaker}: {chunk.text}\n"

        if meeting.transcript:
            meeting.transcript += chunk_text
        else:
            meeting.transcript = chunk_text

        await db.commit()

        logger.debug(f"💾 Stored transcript chunk for meeting {meeting_id}")

    except Exception as e:
        logger.error(f"❌ Failed to store transcript chunk: {e}")
        await db.rollback()

    finally:
        # Always close the session
        await db.close()


# ==================== Status/Debug Endpoints ====================

@router.get("/status/{meeting_id}", response_model=WebSocketConnectionInfo)
async def get_realtime_status(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get real-time transcription status for a meeting.

    Returns:
    - Number of active WebSocket connections
    - Number of Redis subscribers
    """
    from sqlalchemy import select
    result = await db.execute(
        select(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == current_user.id
        )
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    connection_count = ws_manager.get_connection_count(meeting_id)
    subscriber_count = await redis_pubsub.get_active_subscribers(meeting_id)

    return WebSocketConnectionInfo(
        meeting_id=meeting_id,
        active_connections=connection_count,
        redis_subscribers=subscriber_count
    )


@router.post("/test/publish/{meeting_id}")
async def test_publish_message(
    meeting_id: int,
    text: str = "Test transcript message",
    current_user: User = Depends(get_current_user)
):
    """
    **DEBUG ENDPOINT** - Manually publish a test transcript chunk.

    Used for testing WebSocket connections without needing Recall.ai.
    """
    chunk = RealtimeTranscriptChunk(
        meeting_id=meeting_id,
        speaker="Test Speaker",
        text=text,
        timestamp=asyncio.get_event_loop().time(),
        confidence=1.0,
        is_final=True
    )

    await redis_pubsub.publish_transcript_chunk(
        meeting_id=meeting_id,
        chunk_data=chunk.model_dump()
    )

    return {
        "status": "published",
        "meeting_id": meeting_id,
        "text": text
    }
