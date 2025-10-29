"""
Meeting management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.schemas.meeting import (
    MeetingCreate, MeetingResponse, MeetingUpdate, MeetingJoinRequest, MeetingJoinResponse,
    MeetingTranscriptRequest, MeetingTranscriptResponse, TranscriptGetResponse, TranscriptDetailResponse,
    SummarizationRequest, SummarizationResponse
)
from app.schemas.bot import BotResponse, BotDetailResponse, BotsListResponse
from app.services.auth import get_current_user_bearer
from app.services.meeting import (
    create_meeting,
    get_user_meetings,
    get_meeting,
    update_meeting,
    delete_meeting,
    join_meeting_with_twin
)
from app.services.recall_service import recall_service
from app.services.meeting_automation import (
    get_upcoming_auto_join_meetings,
    force_join_meeting
)
from app.services.auto_join_manager import auto_join_manager
# Import AI responses service with error handling
try:
    from app.services import ai_responses
    AI_RESPONSES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI responses service not available: {e}")
    ai_responses = None
    AI_RESPONSES_AVAILABLE = False

# Import your fine-tuned summary service
try:
    from app.services.summarization import generate_meeting_summary, get_summarization_service
    SUMMARY_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Summary service not available: {e}")
    SUMMARY_SERVICE_AVAILABLE = False

from app.models.user import User
from app.models.bot import Bot
from app.models.meeting import Meeting
from app.core.config import settings

router = APIRouter()


async def auto_sync_bot_with_recall(bot: Bot, db: Session, user_id: int) -> Bot:
    """
    Helper function to automatically sync a bot with Recall metadata.
    Returns the updated bot object.
    """
    try:
        # Skip if bot already has a meeting_id and recent update
        if bot.meeting_id and bot.updated_at:
            # Skip if updated within last hour to avoid excessive API calls
            from datetime import timedelta
            if datetime.utcnow() - bot.updated_at < timedelta(hours=1):
                return bot
        
        # Get bot metadata from Recall API
        bot_status_result = await recall_service.get_bot_status(bot.bot_id)
        
        if not bot_status_result:
            return bot  # Return original if can't get status
        
        # Extract meeting information from Recall metadata
        meeting_url_data = bot_status_result.get("meeting_url", {})
        recall_meeting_id = meeting_url_data.get("meeting_id")
        platform = meeting_url_data.get("platform")
        bot_name = bot_status_result.get("bot_name")
        join_time = bot_status_result.get("join_at")
        
        # Try to find matching meeting in database if not already linked
        if not bot.meeting_id and recall_meeting_id:
            # Method 1: Try to find by meeting URL containing the meeting ID
            matching_meeting = db.query(Meeting).filter(
                Meeting.user_id == user_id,
                Meeting.meeting_url.contains(recall_meeting_id)
            ).first()
            
            if not matching_meeting and platform and join_time:
                # Method 2: Try to find by platform and approximate time
                try:
                    from datetime import timedelta
                    join_datetime = datetime.fromisoformat(join_time.replace('Z', '+00:00'))
                    time_window = timedelta(hours=1)
                    
                    matching_meeting = db.query(Meeting).filter(
                        Meeting.user_id == user_id,
                        Meeting.platform == platform,
                        Meeting.scheduled_time >= join_datetime - time_window,
                        Meeting.scheduled_time <= join_datetime + time_window
                    ).first()
                except Exception:
                    pass  # Skip time-based matching if parsing fails
            
            # Associate bot with found meeting
            if matching_meeting:
                bot.meeting_id = matching_meeting.id
        
        # Update bot with platform from Recall if not set
        if platform and not bot.platform:
            bot.platform = platform
        
        # Update bot name if different and not empty
        if bot_name and bot.bot_name != bot_name:
            bot.bot_name = bot_name
        
        # Update timestamp
        bot.updated_at = datetime.utcnow()
        
        return bot
        
    except Exception as e:
        logging.warning(f"Auto-sync failed for bot {bot.bot_id}: {e}")
        return bot  # Return original bot if sync fails


@router.get("/bots", response_model=BotsListResponse)
async def get_my_bots(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    order_by: str = "desc",
    include_meeting_details: bool = False,
    auto_sync_recall: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """Get all bots for current user with optional date filtering and ordering
    
    Args:
        from_date: Start date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        to_date: End date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        order_by: Sort order - 'desc' for newest first (default), 'asc' for oldest first
        include_meeting_details: Include associated meeting title and URL in response
        auto_sync_recall: Automatically sync bots with Recall metadata (default: True)
        limit: Maximum number of results to return
        offset: Number of results to skip
    """
    try:
        # Start with base query for user's bots
        query = db.query(Bot).filter(Bot.user_id == current_user.id)
        
        # Apply date filtering if provided
        filters_applied = {}
        if from_date:
            try:
                from_datetime = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                query = query.filter(Bot.created_at >= from_datetime)
                filters_applied['from_date'] = from_date
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid from_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
                )
        
        if to_date:
            try:
                to_datetime = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                query = query.filter(Bot.created_at <= to_datetime)
                filters_applied['to_date'] = to_date
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid to_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
                )
        
        # Validate order_by parameter
        if order_by.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid order_by value. Use 'asc' for oldest first or 'desc' for newest first"
            )
        
        # Get total count for user's bots (without date filter)
        total_count = db.query(Bot).filter(Bot.user_id == current_user.id).count()
        
        # Apply ordering and pagination
        if order_by.lower() == "asc":
            filtered_query = query.order_by(Bot.created_at.asc())
        else:
            filtered_query = query.order_by(Bot.created_at.desc())
            
        filtered_count = filtered_query.count()
        bots = filtered_query.offset(offset).limit(limit).all()
        
        # Auto-sync bots with Recall metadata if requested
        synced_bots = []
        sync_stats = {"attempted": 0, "successful": 0, "failed": 0}
        
        if auto_sync_recall:
            for bot in bots:
                try:
                    sync_stats["attempted"] += 1
                    synced_bot = await auto_sync_bot_with_recall(bot, db, current_user.id)
                    synced_bots.append(synced_bot)
                    sync_stats["successful"] += 1
                except Exception as e:
                    logging.warning(f"Failed to sync bot {bot.bot_id} with Recall: {e}")
                    synced_bots.append(bot)  # Use original bot if sync fails
                    sync_stats["failed"] += 1
            
            # Commit all sync changes at once
            try:
                db.commit()
            except Exception as e:
                logging.error(f"Failed to commit bot sync changes: {e}")
                db.rollback()
                synced_bots = bots  # Fall back to original bots
        else:
            synced_bots = bots
        
        # Prepare response data
        bot_responses = []
        for bot in synced_bots:
            if include_meeting_details and bot.meeting_id:
                # Get meeting details for this bot
                meeting = db.query(Meeting).filter(Meeting.id == bot.meeting_id).first()
                bot_detail = BotDetailResponse(
                    id=bot.id,
                    bot_id=bot.bot_id,
                    user_id=bot.user_id,
                    platform=bot.platform,
                    bot_name=bot.bot_name,
                    video_download_url=bot.video_download_url,
                    transcript_url=bot.transcript_url,
                    meeting_id=bot.meeting_id,
                    recording_status=bot.recording_status,
                    recording_data=bot.recording_data,
                    video_recording_url=bot.video_recording_url,
                    recording_expires_at=bot.recording_expires_at,
                    created_at=bot.created_at,
                    updated_at=bot.updated_at,
                    # Meeting details
                    meeting_title=meeting.title if meeting else None,
                    meeting_url=meeting.meeting_url if meeting else None,
                    meeting_platform=meeting.platform if meeting else None,
                    meeting_scheduled_time=meeting.scheduled_time if meeting else None,
                    meeting_status=meeting.status if meeting else None
                )
                bot_responses.append(bot_detail)
            else:
                # Use basic bot response
                bot_responses.append(BotResponse.from_orm(bot))
        
        # Add order_by to filters_applied
        if filters_applied is None:
            filters_applied = {}
        filters_applied['order_by'] = order_by
        if include_meeting_details:
            filters_applied['include_meeting_details'] = True
        if auto_sync_recall:
            filters_applied['auto_sync_recall'] = True
            filters_applied['sync_stats'] = sync_stats
        
        return BotsListResponse(
            success=True,
            message=f"Retrieved {len(synced_bots)} bots (ordered by {order_by})" + 
                   (" with meeting details" if include_meeting_details else "") +
                   (f" - Synced {sync_stats['successful']}/{sync_stats['attempted']} bots" if auto_sync_recall else ""),
            data=bot_responses,
            total_count=total_count,
            filtered_count=filtered_count if filters_applied else None,
            filters_applied=filters_applied
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving user bots: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bots: {str(e)}"
        )


@router.get("/bot/{bot_id}/details", response_model=BotDetailResponse)
async def get_bot_details(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db),
    auto_sync_recall: bool = True
):
    """Get detailed bot information including associated meeting details with auto-sync"""
    try:
        # Query bot with meeting details using a join
        bot_query = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot_query:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # Auto-sync with Recall if requested
        if auto_sync_recall:
            try:
                bot_query = await auto_sync_bot_with_recall(bot_query, db, current_user.id)
                db.commit()
            except Exception as e:
                logging.warning(f"Auto-sync failed for bot {bot_id}: {e}")
                db.rollback()
        
        # Get associated meeting details if meeting_id exists
        meeting_details = None
        if bot_query.meeting_id:
            meeting_details = db.query(Meeting).filter(Meeting.id == bot_query.meeting_id).first()
        
        # Create response with bot details and meeting information
        bot_detail = BotDetailResponse(
            id=bot_query.id,
            bot_id=bot_query.bot_id,
            user_id=bot_query.user_id,
            platform=bot_query.platform,
            bot_name=bot_query.bot_name,
            video_download_url=bot_query.video_download_url,
            transcript_url=bot_query.transcript_url,
            meeting_id=bot_query.meeting_id,
            recording_status=bot_query.recording_status,
            recording_data=bot_query.recording_data,
            video_recording_url=bot_query.video_recording_url,
            recording_expires_at=bot_query.recording_expires_at,
            created_at=bot_query.created_at,
            updated_at=bot_query.updated_at,
            # Meeting details
            meeting_title=meeting_details.title if meeting_details else None,
            meeting_url=meeting_details.meeting_url if meeting_details else None,
            meeting_platform=meeting_details.platform if meeting_details else None,
            meeting_scheduled_time=meeting_details.scheduled_time if meeting_details else None,
            meeting_status=meeting_details.status if meeting_details else None
        )
        
        return bot_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving bot details for {bot_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bot details: {str(e)}"
        )


@router.get("/summary/test")
async def test_summary_service():
    """Test endpoint for your fine-tuned summary model"""
    try:
        if not SUMMARY_SERVICE_AVAILABLE:
            return {
                "success": False,
                "message": "Summary service not available",
                "help": "Place your fine-tuned model files in models/weights/ folder"
            }
        
        # Test with sample meeting transcript
        test_transcript = """
        John: Good morning everyone, thanks for joining today's project review meeting.
        Sarah: Hi John, glad to be here. I've prepared the quarterly report.
        Mike: Morning all. I have the technical updates ready to share.
        John: Perfect. Sarah, let's start with your quarterly numbers.
        Sarah: Sure. This quarter we achieved 125% of our target revenue, which is $2.5M total.
        Mike: That's fantastic! On the technical side, we successfully deployed the new API system.
        John: Excellent work team. For next quarter, let's focus on expanding to the European market.
        Sarah: I'll prepare the market analysis by next Friday.
        Mike: I'll work on the technical infrastructure requirements for Europe.
        John: Great. Meeting adjourned. Thanks everyone!
        """
        
        result = generate_meeting_summary(test_transcript)
        
        # Calculate some metrics for the test
        original_words = len(test_transcript.split())
        summary_words = len(result["summary"].split()) if result["summary"] else 0
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        return {
            "success": result["status"] == "success",
            "message": "Summary service test completed",
            "model_status": "fine-tuned FLAN-T5" if result["status"] == "success" else "failed",
            "test_result": {
                "original_words": original_words,
                "summary_words": summary_words,
                "compression_ratio": f"{compression_ratio:.1%}",
                "summary": result["summary"],
                "action_items": result["action_items"],
                "key_decisions": result["key_decisions"]
            },
            "service_available": SUMMARY_SERVICE_AVAILABLE
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "help": "Check if model files are properly placed in models/weights/ folder"
        }


@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_text(
    request: SummarizationRequest,
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Generate summary using the fine-tuned FLAN-T5 model
    """
    try:
        if not SUMMARY_SERVICE_AVAILABLE:
            return SummarizationResponse(
                success=False,
                error="Summarization service not available. Check if model files are in models/weights/ folder."
            )
        
        # Calculate input metrics
        original_words = len(request.text.split())
        
        if request.is_meeting_transcript:
            # Use the full meeting summary function
            result = generate_meeting_summary(request.text)
            
            if result["status"] == "success":
                summary_words = len(result["summary"].split()) if result["summary"] else 0
                
                return SummarizationResponse(
                    success=True,
                    summary=result["summary"],
                    action_items=result["action_items"],
                    key_decisions=result["key_decisions"],
                    metrics={
                        "original_words": original_words,
                        "summary_words": summary_words,
                        "compression_ratio": summary_words / original_words if original_words > 0 else 0,
                        "model_used": "fine-tuned FLAN-T5"
                    }
                )
            else:
                return SummarizationResponse(
                    success=False,
                    error=result.get("error", "Unknown error occurred")
                )
        else:
            # Use simple summarization
            service = get_summarization_service()
            summary = service.generate_summary(
                request.text,
                max_length=request.max_length,
                min_length=request.min_length,
                is_meeting_transcript=False
            )
            
            summary_words = len(summary.split()) if summary else 0
            
            return SummarizationResponse(
                success=True,
                summary=summary,
                metrics={
                    "original_words": original_words,
                    "summary_words": summary_words,
                    "compression_ratio": summary_words / original_words if original_words > 0 else 0,
                    "model_used": "fine-tuned FLAN-T5"
                }
            )
            
    except Exception as e:
        logger.error(f"Error in summarization: {e}")
        return SummarizationResponse(
            success=False,
            error=f"Summarization failed: {str(e)}"
        )


@router.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration"""
    return {
        "recall_api_key_configured": bool(settings.RECALL_API_KEY),
        "recall_api_key_length": len(settings.RECALL_API_KEY) if settings.RECALL_API_KEY else 0,
        "recall_base_url": settings.RECALL_BASE_URL,
        "recall_api_key_last_4": settings.RECALL_API_KEY[-4:] if settings.RECALL_API_KEY else "None"
    }


@router.post("/", response_model=MeetingResponse)
async def create_meeting_schedule(
    meeting: MeetingCreate,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Schedule a meeting for digital twin attendance"""
    return await create_meeting(db, meeting, current_user.id)


@router.get("/", response_model=List[MeetingResponse])
async def get_my_meetings(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    order_by: str = "desc"
):
    """Get all meetings for current user with optional date filtering and ordering
    
    Args:
        from_date: Start date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        to_date: End date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        order_by: Sort order - 'desc' for newest first (default), 'asc' for oldest first
    """
    try:
        # Parse date filters if provided
        from_datetime = None
        to_datetime = None
        
        if from_date:
            try:
                from_datetime = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid from_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
                )
        
        if to_date:
            try:
                to_datetime = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid to_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
                )
        
        # Validate order_by parameter
        if order_by.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid order_by value. Use 'asc' for oldest first or 'desc' for newest first"
            )
        
        return await get_user_meetings(db, current_user.id, from_datetime, to_datetime, order_by)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving user meetings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve meetings: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_details(
    meeting_id: int,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get specific meeting details"""
    meeting = await get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting_schedule(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Update meeting schedule"""
    return await update_meeting(db, meeting_id, meeting_update, current_user.id)


@router.delete("/{meeting_id}")
async def delete_meeting_schedule(
    meeting_id: int,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Delete meeting schedule"""
    await delete_meeting(db, meeting_id, current_user.id)
    return {"message": "Meeting deleted successfully"}


@router.post("/join", response_model=MeetingJoinResponse)
async def join_meeting_with_url(
    request: MeetingJoinRequest,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Join a meeting using the Recall API and save the bot to the database."""
    try:
        # Get user's digital twin settings for bot name and profile picture
        user = db.query(User).filter(User.id == current_user.id).first()
        
        # Use custom bot name from user profile if not provided in request
        if not request.bot_name:
            request.bot_name = user.bot_name if user and user.bot_name else "Digital Twin Bot"
        
        # Use custom profile picture from user profile if not provided in request
        if not hasattr(request, 'profile_picture') or not request.profile_picture:
            if user and user.profile_picture:
                request.profile_picture = user.profile_picture

        # 2. Join the meeting via Recall API
        response_data = await recall_service.join_meeting(request)

        # 3. Save the bot to the database if successful
        if response_data.success and response_data.bot_id:
            existing_bot = db.query(Bot).filter(Bot.bot_id == response_data.bot_id).first()
            if not existing_bot:
                new_bot = Bot(
                    bot_id=response_data.bot_id,
                    user_id=current_user.id,  # Use authenticated user's ID
                    bot_name=request.bot_name,
                    recording_status="pending" if request.enable_video_recording else "not_requested",
                    # platform and meeting_id can be populated later via webhooks or status checks
                )
                db.add(new_bot)
                db.commit()
                
                # If video recording was enabled, note it in the response
                if request.enable_video_recording:
                    response_data.message += " (Video recording enabled)"

        return response_data

    except Exception as e:
        db.rollback()
        logging.error(f"Error in join_meeting: {e}", exc_info=True)
        return MeetingJoinResponse(
            success=False,
            message=f"An unexpected error occurred: {str(e)}",
            bot_id=None,
            status="error",
            meeting_url=request.meeting_url,
            bot_name=request.bot_name,
            error_details={"error_type": type(e).__name__, "error_message": str(e)}
        )


@router.post("/transcript", response_model=MeetingTranscriptResponse)
async def receive_meeting_transcript(
    transcript_data: MeetingTranscriptRequest,
    db: Session = Depends(get_db)
):
    """
    Receive and process the complete meeting transcript from Recall API or other sources.
    
    This endpoint handles:
    1. Storing the full transcript in the database
    2. Generating meeting summary using AI
    3. Extracting action items
    4. Updating meeting and bot records
    
    Example request body:
    {
        "bot_id": "recall_bot_123",
        "meeting_url": "https://zoom.us/j/1234567890",
        "full_transcript": "Complete meeting transcript text...",
        "transcript_segments": [
            {
                "speaker": "John Doe",
                "text": "Hello everyone, let's start the meeting",
                "timestamp": 0.0,
                "start_time": 0.0,
                "end_time": 5.0
            }
        ],
        "participants": ["John Doe", "Jane Smith"],
        "status": "completed"
    }
    """
    try:
        # Find the bot by bot_id
        bot = db.query(Bot).filter(Bot.bot_id == transcript_data.bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=404, 
                detail=f"Bot with ID {transcript_data.bot_id} not found"
            )

        # Prepare the full transcript text
        full_transcript = transcript_data.full_transcript
        if not full_transcript and transcript_data.transcript_segments:
            # Combine transcript segments into full text
            full_transcript = "\n".join([
                f"[{segment.timestamp or 'Unknown Time'}] {segment.speaker or 'Unknown Speaker'}: {segment.text}"
                for segment in transcript_data.transcript_segments
            ])

        if not full_transcript:
            raise HTTPException(
                status_code=400,
                detail="No transcript data provided"
            )

        # Find or create associated meeting
        meeting = None
        if bot.meeting_id:
            meeting = db.query(Meeting).filter(Meeting.id == bot.meeting_id).first()
        
        # If no associated meeting found, try to find by meeting URL
        if not meeting and transcript_data.meeting_url:
            meeting = db.query(Meeting).filter(
                Meeting.meeting_url == transcript_data.meeting_url,
                Meeting.user_id == bot.user_id
            ).first()

        # Update meeting with transcript data
        transcript_saved = False
        if meeting:
            meeting.transcript = full_transcript
            meeting.status = "completed"
            if transcript_data.participants:
                meeting.participants = transcript_data.participants
            meeting.updated_at = datetime.utcnow()
            transcript_saved = True

        # Update bot record
        if transcript_data.meeting_url:
            # Update bot's meeting association if not already set
            if not bot.meeting_id and meeting:
                bot.meeting_id = meeting.id

        # Process transcript with your fine-tuned model for summary generation
        summary_generated = False
        action_items_extracted = False
        
        try:
            if meeting and full_transcript:
                # Try your fine-tuned model first
                if SUMMARY_SERVICE_AVAILABLE:
                    try:
                        logging.info("🤖 Using fine-tuned FLAN-T5 model for summary generation...")
                        summary_result = generate_meeting_summary(full_transcript)
                        
                        if summary_result["success"]:
                            meeting.summary = summary_result["summary"]
                            summary_generated = True
                            logging.info(f"✅ Summary generated: {summary_result['word_count']} words "
                                       f"({summary_result['compression_ratio']:.1%} compression)")
                        else:
                            logging.warning(f"Fine-tuned model failed: {summary_result['summary']}")
                    except Exception as model_error:
                        logging.warning(f"Fine-tuned model error: {model_error}")
                
                # Fallback to AI responses if available
                if not summary_generated and AI_RESPONSES_AVAILABLE and ai_responses:
                    logging.info("📝 Falling back to AI responses service...")
                    try:
                        ai_responses.process_meeting_transcript(
                            meeting_id=meeting.id,
                            transcript=full_transcript,
                            twin_id=meeting.digital_twin_id or 1
                        )
                        summary_generated = True
                        action_items_extracted = True
                    except Exception as ai_error:
                        logging.warning(f"AI responses service failed: {ai_error}")
                
                # If no AI processing succeeded, log warning
                if not summary_generated:
                    logging.warning("No AI processing services available - transcript saved without summary")
                    
        except Exception as processing_error:
            logging.warning(f"Transcript processing failed: {processing_error}")
            # Continue even if processing fails

        # Commit all changes
        db.commit()

        return MeetingTranscriptResponse(
            success=True,
            message="Transcript processed successfully",
            meeting_id=meeting.id if meeting else None,
            transcript_saved=transcript_saved,
            summary_generated=summary_generated,
            action_items_extracted=action_items_extracted
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error processing transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process transcript: {str(e)}"
        )


@router.get("/transcript/{bot_id}")
async def get_meeting_transcript(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get the transcript for a meeting by bot ID"""
    try:
        # Find the bot first and verify it belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        if not bot:
            raise HTTPException(
                status_code=404, 
                detail="Bot not found or you don't have permission to access it"
            )
        
        # Find the associated meeting
        meeting = None
        if bot.meeting_id:
            meeting = db.query(Meeting).filter(Meeting.id == bot.meeting_id).first()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="No meeting associated with this bot")
        
        if not meeting.transcript:
            raise HTTPException(status_code=404, detail="No transcript available for this meeting")
        
        return {
            "bot_id": bot.bot_id,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "meeting_url": meeting.meeting_url,
            "platform": meeting.platform,
            "transcript": meeting.transcript,
            "summary": meeting.summary,
            "action_items": meeting.action_items,
            "participants": meeting.participants,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )

# MAIN ENDPOINT: Get transcripts filtered by bot ID (replaces old implementation)
@router.get("/recall/transcripts/{bot_id}", response_model=TranscriptGetResponse)
async def get_transcripts_by_bot_id(bot_id: str, include_content: bool = False):
    """
    Get transcripts filtered by bot ID using the updated RecallAPIService
    
    Args:
        bot_id: The bot ID to filter transcripts by
        include_content: Whether to fetch and include the actual transcript content
    
    Returns:
        Filtered transcripts for the specified bot ID
    """
    try:
        # Use the new service method to get all transcripts
        all_transcripts_result = await recall_service.list_transcripts()
        
        if not all_transcripts_result.get("success", True):
            return TranscriptGetResponse(
                success=False,
                message=f"Failed to retrieve transcripts: {all_transcripts_result.get('error', 'Unknown error')}",
                data=[]
            )
        
        all_transcripts = all_transcripts_result.get("data", [])
        
        # Filter transcripts by bot_id
        filtered_transcripts = []
        for transcript in all_transcripts:
            # Check if bot_id matches in transcript object or download URL
            transcript_bot_id = transcript.get("bot_id")
            download_url = transcript.get("download_url", "")
            
            # Extract bot_id from download URL if not in transcript object
            if not transcript_bot_id and download_url:
                import re
                bot_id_match = re.search(r'/bots/([^/]+)/', download_url)
                if bot_id_match:
                    transcript_bot_id = bot_id_match.group(1)
            
            # Include if bot_id matches
            if transcript_bot_id == bot_id:
                transcript_data = transcript.copy()
                transcript_data["bot_id"] = transcript_bot_id
                
                # Fetch content if requested
                if include_content and download_url:
                    try:
                        content_result = await recall_service.fetch_and_format_transcript_from_url(download_url)
                        if content_result.get("success"):
                            transcript_data["content"] = content_result.get("content")
                            transcript_data["formatted_content"] = content_result.get("formatted_content")
                    except Exception as content_error:
                        logging.warning(f"Failed to fetch content for transcript {transcript.get('id')}: {content_error}")
                        transcript_data["content_error"] = str(content_error)
                
                filtered_transcripts.append(transcript_data)
        
        return TranscriptGetResponse(
            success=True,
            message=f"Found {len(filtered_transcripts)} transcripts for bot {bot_id}",
            data=filtered_transcripts,
            bot_id=bot_id,
            total_count=len(filtered_transcripts)
        )
        
    except Exception as e:
        logging.error(f"Error retrieving transcripts for bot {bot_id}: {e}", exc_info=True)
        return TranscriptGetResponse(
            success=False,
            message=f"Failed to retrieve transcripts for bot {bot_id}: {str(e)}",
            data=[],
            bot_id=bot_id,
            error_details={"exception": str(e)}
        )



@router.get("/recall/bot/{bot_id}/status")
async def get_bot_status(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get the current status of a bot"""
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        result = await recall_service.get_bot_status(bot_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving bot status for {bot_id}: {e}", exc_info=True)
        return {
            "error": f"Failed to retrieve bot status: {str(e)}",
            "bot_id": bot_id
        }


@router.get("/recall/recordings")
async def list_recordings(bot_id: str = None, limit: int = 50):
    """List recordings, optionally filtered by bot ID"""
    try:
        result = await recall_service.list_recordings(bot_id=bot_id, limit=limit)
        return result
    except Exception as e:
        logging.error(f"Error listing recordings: {e}", exc_info=True)
        return {
            "error": f"Failed to list recordings: {str(e)}"
        }


@router.get("/recall/meeting-metadata")
async def list_meeting_metadata(bot_id: str = None, limit: int = 50):
    """List meeting metadata, optionally filtered by bot ID"""
    try:
        result = await recall_service.list_meeting_metadata(bot_id=bot_id, limit=limit)
        return result
    except Exception as e:
        logging.error(f"Error listing meeting metadata: {e}", exc_info=True)
        return {
            "error": f"Failed to list meeting metadata: {str(e)}"
        }


@router.post("/recall/transcript/{transcript_id}/fetch-content")
async def fetch_transcript_content(transcript_id: str):
    """Fetch and format the actual transcript content from a transcript ID"""
    try:
        # First get the transcript to get the download URL
        transcript_result = await recall_service.get_transcript_by_id(transcript_id)
        
        if transcript_result.get("error"):
            return {
                "success": False,
                "error": transcript_result["error"]
            }
        
        download_url = transcript_result.get("download_url")
        if not download_url:
            return {
                "success": False,
                "error": "No download URL found for transcript"
            }
        
        # Fetch and format the content
        content_result = await recall_service.fetch_and_format_transcript_from_url(download_url)
        return content_result
        
    except Exception as e:
        logging.error(f"Error fetching transcript content for {transcript_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to fetch transcript content: {str(e)}"
        }


@router.post("/recall/bot/{bot_id}/stop")
async def stop_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Stop a bot and end the meeting recording"""
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to stop it"
            )
        
        result = await recall_service.stop_bot(bot_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error stopping bot {bot_id}: {e}", exc_info=True)
        return {
            "error": f"Failed to stop bot: {str(e)}",
            "bot_id": bot_id
        }


@router.get("/recall/bot/{bot_id}/metadata")
async def get_bot_metadata_from_recall(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get comprehensive bot metadata from Recall API including meeting details"""
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # Get bot status and details from Recall
        bot_status_result = await recall_service.get_bot_status(bot_id)
        
        # Get meeting metadata for this bot
        meeting_metadata_result = await recall_service.list_meeting_metadata(bot_id=bot_id)
        
        # Get recordings metadata
        recordings_result = await recall_service.list_recordings(bot_id=bot_id)
        
        return {
            "success": True,
            "bot_id": bot_id,
            "bot_status": bot_status_result,
            "meeting_metadata": meeting_metadata_result,
            "recordings_metadata": recordings_result,
            "database_bot_info": {
                "id": bot.id,
                "bot_name": bot.bot_name,
                "platform": bot.platform,
                "meeting_id": bot.meeting_id,
                "recording_status": bot.recording_status,
                "created_at": bot.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving bot metadata for {bot_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to retrieve bot metadata: {str(e)}",
            "bot_id": bot_id
        }


@router.get("/recall/bots/detailed")
async def list_bots_with_details():
    """List all bots from Recall API with detailed information including meeting metadata"""
    try:
        # Get all bots from Recall
        bots_result = await recall_service.list_bots()
        
        # For each bot, try to get additional metadata
        detailed_bots = []
        for bot in bots_result:
            bot_id = bot.get("id")
            if bot_id:
                try:
                    # Get bot status
                    status = await recall_service.get_bot_status(bot_id)
                    
                    # Get meeting metadata
                    meeting_metadata = await recall_service.list_meeting_metadata(bot_id=bot_id)
                    
                    detailed_bot = {
                        "bot_info": bot,
                        "status": status,
                        "meeting_metadata": meeting_metadata,
                        "bot_id": bot_id
                    }
                    detailed_bots.append(detailed_bot)
                except Exception as e:
                    # If individual bot fails, still include basic info
                    detailed_bots.append({
                        "bot_info": bot,
                        "error": f"Failed to get details: {str(e)}",
                        "bot_id": bot_id
                    })
        
        return {
            "success": True,
            "total_bots": len(bots_result),
            "detailed_bots": detailed_bots
        }
    except Exception as e:
        logging.error(f"Error listing detailed bots: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to list detailed bots: {str(e)}"
        }


@router.get("/recall/bots")
async def list_bots():
    """List all bots"""
    try:
        result = await recall_service.list_bots()
        return {
            "success": True,
            "bots": result
        }
    except Exception as e:
        logging.error(f"Error listing bots: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to list bots: {str(e)}"
        }


@router.post("/recall/bot/{bot_id}/store-transcript")
async def store_comprehensive_transcript(bot_id: str, storage_path: str = "transcripts/"):
    """Store comprehensive transcript data locally"""
    try:
        result = await recall_service.store_comprehensive_transcript(bot_id, storage_path)
        return result
    except Exception as e:
        logging.error(f"Error storing transcript for bot {bot_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to store transcript: {str(e)}",
            "bot_id": bot_id
        }

@router.get("/bot/{bot_id}/transcript")
async def get_bot_transcript(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Get the complete transcript for a meeting using official Recall API endpoints
    """
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # First, get the list of transcripts for this bot
        transcripts_result = await recall_service.list_transcripts(bot_id=bot_id)

        if not transcripts_result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve transcripts: {transcripts_result.get('error', 'Unknown error')}",
            )

        transcripts = transcripts_result.get("transcripts", [])
        
        if not transcripts:
            raise HTTPException(
                status_code=404,
                detail="No transcripts found for this bot. The meeting may still be in progress or no transcript was generated.",
            )

        # Get the most recent transcript (assuming the first one is the latest)
        latest_transcript = transcripts[0]
        transcript_id = latest_transcript.get("id")

        if not transcript_id:
            raise HTTPException(
                status_code=400,
                detail="Transcript found but no ID available",
            )

        # Get detailed transcript data
        detailed_transcript = await recall_service.get_transcript_by_id(transcript_id)

        if not detailed_transcript.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve detailed transcript: {detailed_transcript.get('error', 'Unknown error')}",
            )

        return {
            "success": True,
            "bot_id": bot_id,
            "transcript_count": len(transcripts),
            "transcript_id": transcript_id,
            "transcript_data": detailed_transcript["transcript_data"],
            "processed_chunks": detailed_transcript["processed_chunks"],
            "total_words": detailed_transcript["total_words"],
            "duration": detailed_transcript["duration"],
            "status": detailed_transcript["status"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving transcript: {str(e)}"
        )

@router.get("/bot/{bot_id}/transcript/formatted")
async def get_formatted_transcript(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Get the formatted transcript for a meeting by fetching from the download URL
    """
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # First, get the list of transcripts for this bot
        transcripts_result = await recall_service.list_transcripts(bot_id=bot_id)

        if not transcripts_result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve transcripts: {transcripts_result.get('error', 'Unknown error')}",
            )

        transcripts = transcripts_result.get("transcripts", [])
        
        if not transcripts:
            raise HTTPException(
                status_code=404,
                detail="No transcripts found for this bot. The meeting may still be in progress or no transcript was generated.",
            )

        # Get the most recent transcript
        latest_transcript = transcripts[0]
        
        # The download URL is nested inside the 'data' object
        transcript_data = latest_transcript.get("data", {})
        download_url = transcript_data.get("download_url")

        if not download_url:
            raise HTTPException(
                status_code=400,
                detail=f"Transcript found but no download URL available. Available data keys: {list(transcript_data.keys())}",
            )

        # Fetch and format the transcript from the download URL
        formatted_result = await recall_service.fetch_and_format_transcript_from_url(download_url)

        if not formatted_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch transcript: {formatted_result.get('error', 'Unknown error')}",
            )

        return {
            "success": True,
            "bot_id": bot_id,
            "transcript_id": latest_transcript.get("id"),
            "download_url": download_url,
            "formatted_transcript": formatted_result["formatted_transcript"],
            "clean_continuous_text": formatted_result["formatted_transcript"].get("clean_continuous_text", ""),
            "statistics": formatted_result["statistics"],
            "metadata": {
                "transcript_status": latest_transcript.get("status"),
                "transcript_created": latest_transcript.get("created_at"),
                "bot_id": latest_transcript.get("bot_id"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving formatted transcript: {str(e)}"
        )


@router.post("/{meeting_id}/force-join")
async def force_join_meeting_endpoint(
    meeting_id: int,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Manually trigger auto-join for a specific meeting"""
    try:
        # Verify the meeting belongs to the current user
        meeting = await get_meeting(db, meeting_id, current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        result = force_join_meeting(meeting_id)
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "message": f"Auto-join triggered for meeting {meeting_id}",
            "task_id": result.get("task_id"),
            "status": result["status"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering auto-join: {str(e)}")


@router.post("/{meeting_id}/toggle-auto-join")
async def toggle_auto_join(
    meeting_id: int,
    auto_join: bool,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Toggle auto-join setting for a meeting"""
    try:
        meeting = await get_meeting(db, meeting_id, current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Store original status for comparison
        original_status = meeting.status
        
        # Only update the auto_join field
        meeting.auto_join = auto_join
        db.commit()
        db.refresh(meeting)
        
        # Check if the meeting is within the auto-join window
        from datetime import datetime, timedelta
        from app.core.config import settings
        
        now = datetime.utcnow()
        join_window_start = now
        join_window_end = now + timedelta(minutes=settings.AUTO_JOIN_ADVANCE_MINUTES)
        
        warning_message = ""
        if (auto_join and meeting.scheduled_time >= join_window_start and 
            meeting.scheduled_time <= join_window_end and original_status == "scheduled"):
            warning_message = f" Note: Meeting is within auto-join window ({settings.AUTO_JOIN_ADVANCE_MINUTES} minutes), so it may be automatically joined soon by the background scheduler."
        
        return {
            "success": True,
            "message": f"Auto-join {'enabled' if auto_join else 'disabled'} for meeting {meeting_id}{warning_message}",
            "meeting_id": meeting_id,
            "auto_join": auto_join,
            "status": meeting.status,
            "scheduled_time": meeting.scheduled_time,
            "auto_join_advance_minutes": settings.AUTO_JOIN_ADVANCE_MINUTES
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling auto-join: {str(e)}")


@router.get("/bot/{bot_id}/recording-url")
async def get_and_update_recording_url(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Get the recording download URL for a bot and update it in the database
    """
    try:
        # Find the bot in the database and verify it belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        if not bot:
            raise HTTPException(
                status_code=404, 
                detail="Bot not found in database or you don't have permission to access it"
            )
        
        # Get recordings from Recall API
        recordings_result = await recall_service.get_bot_recordings(bot_id)
        
        if not recordings_result.success:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve recordings: {recordings_result.message}"
            )
        
        if not recordings_result.recordings:
            raise HTTPException(
                status_code=404,
                detail="No recordings found for this bot"
            )
        
        # Get the most recent recording
        latest_recording = recordings_result.recordings[0]
        
        # Extract download URL from video_mixed media shortcut
        download_url = None
        if latest_recording.media_shortcuts and "video_mixed" in latest_recording.media_shortcuts:
            video_data = latest_recording.media_shortcuts["video_mixed"]
            download_url = video_data.get("data", {}).get("download_url")
        
        if not download_url:
            raise HTTPException(
                status_code=404,
                detail="No video download URL found in recording"
            )
        
        # Update the bot in the database
        bot.video_recording_url = download_url
        bot.video_download_url = download_url  # Also update this field for compatibility
        bot.recording_status = "completed"
        bot.recording_data = {
            "recording_id": latest_recording.id,
            "created_at": latest_recording.created_at.isoformat() if latest_recording.created_at else None,
            "completed_at": latest_recording.completed_at.isoformat() if latest_recording.completed_at else None,
            "status": latest_recording.status
        }
        bot.recording_expires_at = latest_recording.expires_at
        bot.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "bot_id": bot_id,
            "download_url": download_url,
            "recording_id": latest_recording.id,
            "recording_status": latest_recording.status,
            "database_updated": True,
            "expires_at": latest_recording.expires_at.isoformat() if latest_recording.expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error getting recording URL for bot {bot_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recording URL: {str(e)}"
        )


@router.get("/bot/{bot_id}/recording-url/simple")
async def get_recording_url_simple(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Get just the recording download URL for a bot (without database update)
    """
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # Get recordings from Recall API
        recordings_result = await recall_service.get_bot_recordings(bot_id)
        
        if not recordings_result.success:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to retrieve recordings: {recordings_result.message}"
            )
        
        if not recordings_result.recordings:
            raise HTTPException(
                status_code=404,
                detail="No recordings found for this bot"
            )
        
        # Get the most recent recording
        latest_recording = recordings_result.recordings[0]
        
        # Extract download URL from video_mixed media shortcut
        download_url = None
        if latest_recording.media_shortcuts and "video_mixed" in latest_recording.media_shortcuts:
            video_data = latest_recording.media_shortcuts["video_mixed"]
            download_url = video_data.get("data", {}).get("download_url")
        
        if not download_url:
            raise HTTPException(
                status_code=404,
                detail="No video download URL found in recording"
            )
        
        return {
            "success": True,
            "bot_id": bot_id,
            "download_url": download_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting recording URL for bot {bot_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recording URL: {str(e)}"
        )


@router.post("/bot/{bot_id}/sync-with-recall")
async def sync_bot_with_recall_metadata(
    bot_id: str,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Sync bot with meeting data from Recall API metadata.
    This will attempt to associate the bot with an existing meeting in the database
    based on meeting URL, platform, and other matching criteria.
    """
    try:
        # Verify the bot belongs to the current user
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=404,
                detail="Bot not found or you don't have permission to access it"
            )
        
        # Get bot metadata from Recall API
        bot_status_result = await recall_service.get_bot_status(bot_id)
        
        if not bot_status_result:
            raise HTTPException(
                status_code=404,
                detail="Could not retrieve bot metadata from Recall API"
            )
        
        # Extract meeting information from Recall metadata
        meeting_url_data = bot_status_result.get("meeting_url", {})
        recall_meeting_id = meeting_url_data.get("meeting_id")
        platform = meeting_url_data.get("platform")
        bot_name = bot_status_result.get("bot_name")
        join_time = bot_status_result.get("join_at")
        
        # Try to find matching meeting in database
        matching_meeting = None
        update_info = {
            "recall_metadata": {
                "meeting_id": recall_meeting_id,
                "platform": platform,
                "join_time": join_time,
                "bot_name": bot_name
            }
        }
        
        if recall_meeting_id:
            # Method 1: Try to find by meeting URL containing the meeting ID
            matching_meeting = db.query(Meeting).filter(
                Meeting.user_id == current_user.id,
                Meeting.meeting_url.contains(recall_meeting_id)
            ).first()
            
            if matching_meeting:
                update_info["match_method"] = "meeting_url_contains_id"
        
        if not matching_meeting and platform:
            # Method 2: Try to find by platform and approximate time
            from datetime import timedelta
            
            if join_time:
                try:
                    join_datetime = datetime.fromisoformat(join_time.replace('Z', '+00:00'))
                    # Look for meetings scheduled within 1 hour of bot join time
                    time_window = timedelta(hours=1)
                    
                    matching_meeting = db.query(Meeting).filter(
                        Meeting.user_id == current_user.id,
                        Meeting.platform == platform,
                        Meeting.scheduled_time >= join_datetime - time_window,
                        Meeting.scheduled_time <= join_datetime + time_window
                    ).first()
                    
                    if matching_meeting:
                        update_info["match_method"] = "platform_and_time_window"
                except Exception as e:
                    logging.warning(f"Could not parse join time: {e}")
        
        if not matching_meeting:
            # Method 3: Try to find the most recent meeting with same platform
            if platform:
                matching_meeting = db.query(Meeting).filter(
                    Meeting.user_id == current_user.id,
                    Meeting.platform == platform
                ).order_by(Meeting.scheduled_time.desc()).first()
                
                if matching_meeting:
                    update_info["match_method"] = "latest_meeting_same_platform"
        
        # Update bot with found meeting or Recall metadata
        changes_made = []
        
        if matching_meeting:
            # Associate bot with found meeting
            if bot.meeting_id != matching_meeting.id:
                bot.meeting_id = matching_meeting.id
                changes_made.append(f"Linked to meeting: {matching_meeting.title}")
        
        # Update bot with platform from Recall if not set
        if platform and bot.platform != platform:
            bot.platform = platform
            changes_made.append(f"Updated platform: {platform}")
        
        # Update bot name if different
        if bot_name and bot.bot_name != bot_name:
            bot.bot_name = bot_name
            changes_made.append(f"Updated bot name: {bot_name}")
        
        # Update bot's updated_at timestamp
        bot.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        db.refresh(bot)
        
        # Prepare response with meeting details if associated
        response_data = {
            "success": True,
            "bot_id": bot_id,
            "changes_made": changes_made,
            "recall_metadata": update_info["recall_metadata"],
            "match_info": {
                "method": update_info.get("match_method"),
                "meeting_found": matching_meeting is not None
            },
            "updated_bot": {
                "id": bot.id,
                "bot_id": bot.bot_id,
                "bot_name": bot.bot_name,
                "platform": bot.platform,
                "meeting_id": bot.meeting_id,
                "recording_status": bot.recording_status,
                "created_at": bot.created_at,
                "updated_at": bot.updated_at
            }
        }
        
        # Add meeting details if associated
        if matching_meeting:
            response_data["meeting_details"] = {
                "id": matching_meeting.id,
                "title": matching_meeting.title,
                "meeting_url": matching_meeting.meeting_url,
                "platform": matching_meeting.platform,
                "scheduled_time": matching_meeting.scheduled_time,
                "status": matching_meeting.status,
                "description": matching_meeting.description
            }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error syncing bot {bot_id} with Recall metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync bot with Recall metadata: {str(e)}"
        )