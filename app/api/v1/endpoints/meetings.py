"""
Meeting management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from app.core.database import get_db
from app.schemas.meeting import (
    MeetingCreate, MeetingResponse, MeetingUpdate, MeetingJoinRequest, MeetingJoinResponse,
    MeetingTranscriptRequest, MeetingTranscriptResponse, TranscriptGetResponse, TranscriptDetailResponse
)
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
# Import AI responses service with error handling
try:
    from app.services import ai_responses
    AI_RESPONSES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI responses service not available: {e}")
    ai_responses = None
    AI_RESPONSES_AVAILABLE = False

from app.models.user import User
from app.models.bot import Bot
from app.models.meeting import Meeting
from app.core.config import settings

router = APIRouter()


@router.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration"""
    return {
        "recall_api_key_configured": bool(settings.RECALL_API_KEY),
        "recall_api_key_length": len(settings.RECALL_API_KEY) if settings.RECALL_API_KEY else 0,
        "recall_base_url": settings.RECALL_BASE_URL,
        "recall_api_key_last_4": settings.RECALL_API_KEY[-4:] if settings.RECALL_API_KEY else "None"
    }


@router.post("/debug/test-auth")
async def test_recall_auth():
    """Test Recall API authentication"""
    return await recall_service.test_authentication()


@router.post("/", response_model=MeetingResponse)
async def create_meeting_schedule(
    meeting: MeetingCreate,
    db: Session = Depends(get_db)
):
    """Schedule a meeting for digital twin attendance"""
    # return await create_meeting(db, meeting, current_user.id)
    return await create_meeting(db, meeting, 1)  # Using dummy user_id = 1


@router.get("/", response_model=List[MeetingResponse])
async def get_my_meetings(
    db: Session = Depends(get_db)
):
    """Get all meetings for current user"""
    # return await get_user_meetings(db, current_user.id)
    return await get_user_meetings(db, 1)  # Using dummy user_id = 1


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_details(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Get specific meeting details"""
    # meeting = await get_meeting(db, meeting_id, current_user.id)
    meeting = await get_meeting(db, meeting_id, 1)  # Using dummy user_id = 1
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting_schedule(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    db: Session = Depends(get_db)
):
    """Update meeting schedule"""
    # return await update_meeting(db, meeting_id, meeting_update, current_user.id)
    return await update_meeting(db, meeting_id, meeting_update, 1)  # Using dummy user_id = 1


@router.delete("/{meeting_id}")
async def delete_meeting_schedule(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Delete meeting schedule"""
    # await delete_meeting(db, meeting_id, current_user.id)
    await delete_meeting(db, meeting_id, 1)  # Using dummy user_id = 1
    return {"message": "Meeting deleted successfully"}


@router.post("/{meeting_id}/join")
async def join_meeting(
    meeting_id: int,
    twin_id: int,
    db: Session = Depends(get_db)
):
    """Join meeting with digital twin"""
    # return await join_meeting_with_twin(db, meeting_id, twin_id, current_user.id)
    return await join_meeting_with_twin(db, meeting_id, twin_id, 1)  # Using dummy user_id = 1


@router.post("/join", response_model=MeetingJoinResponse)
async def join_meeting_with_url(
    request: MeetingJoinRequest,
    db: Session = Depends(get_db)
):
    """Join a meeting using the Recall API and save the bot to the database."""
    try:
        # Set default bot name if not provided
        if not request.bot_name:
            request.bot_name = "Digital Twin Bot"

        # 2. Join the meeting via Recall API
        response_data = await recall_service.join_meeting(request)

        # 3. Save the bot to the database if successful
        if response_data.success and response_data.bot_id:
            existing_bot = db.query(Bot).filter(Bot.bot_id == response_data.bot_id).first()
            if not existing_bot:
                # Use the bot name from request
                bot_name = request.bot_name
                new_bot = Bot(
                    bot_id=response_data.bot_id,
                    user_id=1,  # Using dummy user_id = 1
                    bot_name=bot_name,
                    # platform and meeting_id can be populated later via webhooks or status checks
                )
                db.add(new_bot)
                db.commit()

        return response_data

    except Exception as e:
        db.rollback()
        logging.error(f"Error in join_meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


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

        # Process transcript with AI for summary and action items
        summary_generated = False
        action_items_extracted = False
        
        try:
            if meeting and AI_RESPONSES_AVAILABLE and ai_responses:
                # Use the AI service to process the transcript
                ai_responses.process_meeting_transcript(
                    meeting_id=meeting.id,
                    transcript=full_transcript,
                    twin_id=meeting.digital_twin_id or 1  # Use default twin if none specified
                )
                summary_generated = True
                action_items_extracted = True
            elif meeting:
                # If AI is not available, just log a warning
                logging.warning("AI responses service not available - skipping AI processing")
        except Exception as ai_error:
            logging.warning(f"AI processing failed for transcript: {ai_error}")
            # Continue even if AI processing fails

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
    db: Session = Depends(get_db)
):
    """Get the transcript for a meeting by bot ID"""
    try:
        # Find the bot first
        bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
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


@router.get("/{meeting_id}/transcript")
async def get_meeting_transcript_by_meeting_id(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Get the transcript for a specific meeting by meeting ID"""
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if not meeting.transcript:
            raise HTTPException(status_code=404, detail="No transcript available for this meeting")
        
        # Find associated bot if any
        bot = db.query(Bot).filter(Bot.meeting_id == meeting_id).first()
        
        return {
            "bot_id": bot.bot_id if bot else None,
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


@router.get("/transcripts/all")
async def get_all_transcripts(
    db: Session = Depends(get_db)
):
    """Get all meetings with transcripts for the current user"""
    try:
        # meetings = db.query(Meeting).filter(
        #     Meeting.user_id == current_user.id,
        #     Meeting.transcript.isnot(None)
        # ).all()
        meetings = db.query(Meeting).filter(Meeting.transcript.isnot(None)).all()  # Using dummy user access
        
        transcripts = []
        for meeting in meetings:
            transcripts.append({
                "meeting_id": meeting.id,
                "title": meeting.title,
                "meeting_url": meeting.meeting_url,
                "platform": meeting.platform,
                "scheduled_time": meeting.scheduled_time,
                "status": meeting.status,
                "transcript_available": bool(meeting.transcript),
                "summary_available": bool(meeting.summary),
                "action_items_available": bool(meeting.action_items),
                "created_at": meeting.created_at,
                "updated_at": meeting.updated_at
            })
        
        return {
            "total_transcripts": len(transcripts),
            "transcripts": transcripts
        }
        
    except Exception as e:
        logging.error(f"Error retrieving transcripts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcripts: {str(e)}"
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


# Updated endpoints using the comprehensive RecallAPIService

@router.get("/recall/comprehensive/{bot_id}")
async def get_comprehensive_meeting_data(bot_id: str):
    """Get comprehensive meeting data including recordings, transcripts, and metadata"""
    try:
        result = await recall_service.get_comprehensive_meeting_data(bot_id)
        return result
    except Exception as e:
        logging.error(f"Error retrieving comprehensive data for bot {bot_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to retrieve comprehensive data: {str(e)}",
            "bot_id": bot_id
        }


@router.get("/recall/bot/{bot_id}/status")
async def get_bot_status(bot_id: str):
    """Get the current status of a bot"""
    try:
        result = await recall_service.get_bot_status(bot_id)
        return result
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
async def stop_bot(bot_id: str):
    """Stop a bot and end the meeting recording"""
    try:
        result = await recall_service.stop_bot(bot_id)
        return result
    except Exception as e:
        logging.error(f"Error stopping bot {bot_id}: {e}", exc_info=True)
        return {
            "error": f"Failed to stop bot: {str(e)}",
            "bot_id": bot_id
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
    bot_id: str
):
    """
    Get the complete transcript for a meeting using official Recall API endpoints
    """
    try:
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
    bot_id: str
):
    """
    Get the formatted transcript for a meeting by fetching from the download URL
    """
    try:
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

