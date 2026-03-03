"""
Summarization endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path

from app.core.database import get_db
from app.services.auth import get_current_user_bearer
from app.schemas.meeting import SummarizationResponse  # Import from schemas
# Import summarization service with error handling
try:
    from app.services.summarization import generate_simple_meeting_summary
    SUMMARIZATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Summarization service not available: {e}")
    generate_simple_meeting_summary = None
    SUMMARIZATION_AVAILABLE = False
from app.services.recall_service import recall_service
from app.models.user import User
from app.models.meeting import Meeting
from app.models.bot import Bot
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

router = APIRouter()

# Helper function to log bot_id filtering issues to JSON
def log_bot_filtering_to_json(endpoint: str, requested_bot_id: str, data: dict):
    """Log bot_id filtering debug info to JSON file"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "bot_filtering_debug.json"
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "requested_bot_id": requested_bot_id,
            **data
        }
        
        # Append to file
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []
        
        existing_logs.append(log_entry)
        
        # Keep only last 50 entries
        if len(existing_logs) > 50:
            existing_logs = existing_logs[-50:]
        
        with open(log_file, 'w') as f:
            json.dump(existing_logs, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write to JSON log: {e}")


class SummarizationRequest(BaseModel):
    pass  # No bot_id needed, will get latest bot automatically


class BotSummarizationRequest(BaseModel):
    bot_id: str  # UUID string


class DirectTranscriptRequest(BaseModel):
    """Request for direct transcript summarization"""
    transcript: str


@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_transcript(
    request: DirectTranscriptRequest,
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Generate summary directly from transcript text

    This is a simple endpoint that takes raw transcript text and returns a summary.
    No bot or meeting required - just send the text and get the summary.

    Request body:
    {
        "transcript": "Your meeting transcript text here..."
    }

    Returns:
    {
        "success": true,
        "summary": "Generated summary...",
        "metrics": {
            "original_words": 450,
            "summary_words": 120,
            "compression_ratio": 0.27,
            "model_used": "flan-t5-base-finetuned"
        }
    }
    """
    try:
        if not SUMMARIZATION_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Summarization service is not available. Please ensure PyTorch and transformers are installed."
            )

        transcript = request.transcript.strip()

        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript text cannot be empty"
            )

        # Log request info
        word_count = len(transcript.split())
        char_count = len(transcript)
        logger.info(f"Direct summarization request from user {current_user.id}: {word_count} words, {char_count} chars")

        # Generate summary
        summary = generate_simple_meeting_summary(transcript)

        # Calculate metrics
        original_words = len(transcript.split())
        summary_words = len(summary.split())
        compression_ratio = summary_words / original_words if original_words > 0 else 0

        logger.info(f"Summary generated: {summary_words} words ({compression_ratio:.1%} compression)")

        return SummarizationResponse(
            success=True,
            summary=summary,
            metrics={
                "original_words": original_words,
                "summary_words": summary_words,
                "compression_ratio": compression_ratio,
                "model_used": "flan-t5-base-finetuned"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in direct transcript summarization: {e}")
        return SummarizationResponse(
            success=False,
            error=str(e)
        )


@router.post("/generate", response_model=SummarizationResponse)
async def generate_bot_meeting_summary(
    request: SummarizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Generate summary for meeting transcripts using formatted transcript and continuous text
    
    This endpoint:
    1. Automatically finds the latest bot created by the current user
    2. Fetches the formatted transcript for that bot from recall service
    3. Extracts the continuous_text from the JSON formatted transcript
    4. Generates a comprehensive summary using the fine-tuned FLAN-T5 model
    5. Returns the summary with debug information showing the input transcript
    """
    try:
        # Get the latest bot for the current user (ordered by created_at desc)
        latest_bot = db.query(Bot).filter(
            Bot.user_id == current_user.id
        ).order_by(Bot.created_at.desc()).first()
        
        if not latest_bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No bots found for this user"
            )
        
        bot_id = latest_bot.bot_id  # Use UUID bot_id, not integer id
        logger.info(f"Using latest bot {bot_id} for user {current_user.id}")
        
        # Get the formatted transcript from recall service
        transcripts_result = await recall_service.list_transcripts(bot_id=str(bot_id))
        
        if not transcripts_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to retrieve transcripts for bot {bot_id}: {transcripts_result.get('error', 'Unknown error')}"
            )
        
        transcripts = transcripts_result.get("transcripts", [])
        if not transcripts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transcripts found for bot {bot_id}. The meeting may still be in progress or no transcript was generated."
            )
        
        # Get the most recent transcript
        latest_transcript = transcripts[0]
        transcript_data = latest_transcript.get("data", {})
        download_url = transcript_data.get("download_url")
        
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcript found but no download URL available for bot {bot_id}"
            )
        
        # Fetch and format the transcript from the download URL
        formatted_result = await recall_service.fetch_and_format_transcript_from_url(download_url)
        
        if not formatted_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch formatted transcript: {formatted_result.get('error', 'Unknown error')}"
            )
        
        # Extract the formatted transcript data
        formatted_transcript = formatted_result.get("formatted_transcript", {})
        continuous_text = formatted_transcript.get("clean_continuous_text", "")
        
        # Fallback to timestamped version if clean version not available
        if not continuous_text:
            continuous_text = formatted_transcript.get("continuous_text", "")
        
        if not continuous_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No continuous text found in formatted transcript"
            )
        
        # For debug: create a preview of the continuous text (first 500 chars)
        transcript_preview = continuous_text[:500] + "..." if len(continuous_text) > 500 else continuous_text
        
        logger.info(f"Generating summary for bot {bot_id} using formatted transcript")
        logger.info(f"Continuous text length: {len(continuous_text)} characters")
        logger.info(f"Transcript preview: {transcript_preview}")
        
        # Generate the summary using our fine-tuned model
        summary = generate_simple_meeting_summary(continuous_text)
        
        # Calculate metrics
        original_words = len(continuous_text.split())
        summary_words = len(summary.split())
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        logger.info(f"Summary generated successfully for bot {bot_id}")
        logger.info(f"Compression: {original_words} words -> {summary_words} words ({compression_ratio:.1%})")
        
        return SummarizationResponse(
            success=True,
            summary=summary,
            metrics={
                "original_words": original_words,
                "summary_words": summary_words,
                "compression_ratio": compression_ratio,
                "model_used": "flan-t5-large"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error generating summary for user {current_user.id}: {e}")
        # Try to get bot_id if available
        try:
            latest_bot = db.query(Bot).filter(
                Bot.user_id == current_user.id
            ).order_by(Bot.created_at.desc()).first()
            error_bot_id = latest_bot.bot_id if latest_bot else ""
        except:
            error_bot_id = ""
        
        return SummarizationResponse(
            success=False,
            error=str(e)
        )


@router.post("/generate/{bot_id}", response_model=SummarizationResponse)
async def generate_summary_for_specific_bot(
    bot_id: str,  # Changed from int to str to support UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Generate summary for a specific bot's meeting transcripts
    
    This endpoint:
    1. Takes a bot_id as a path parameter (UUID string)
    2. Verifies the bot belongs to the current user
    3. Fetches the formatted transcript for that bot from recall service
    4. Extracts the continuous_text from the JSON formatted transcript
    5. Generates a comprehensive summary using the fine-tuned FLAN-T5 model
    6. Returns the summary with debug information showing the input transcript
    
    Args:
        bot_id: The UUID of the bot to generate summary for (e.g., "87abdf5f-836d-4422-a7b4-445124a1cc9d")
    """
    try:
        # Get the specific bot and verify it belongs to the current user
        # Note: bot_id is the UUID stored in the bot_id column, not the integer id
        bot = db.query(Bot).filter(
            Bot.bot_id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot {bot_id} not found or does not belong to current user"
            )
        
        logger.info(f"🔍 Generating summary for bot {bot_id} for user {current_user.id}")
        
        # Get the formatted transcript from recall service
        transcripts_result = await recall_service.list_transcripts(bot_id=bot_id)
        
        if not transcripts_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to retrieve transcripts for bot {bot_id}: {transcripts_result.get('error', 'Unknown error')}"
            )
        
        all_transcripts = transcripts_result.get("transcripts", [])
        logger.info(f"📊 Recall API returned {len(all_transcripts)} transcripts")
        
        # Prepare data for JSON logging
        transcript_list = []
        
        # Filter transcripts to ensure they match the bot_id
        # The Recall API returns null bot_ids, so extract from download URL
        transcripts = []
        import re
        for transcript in all_transcripts:
            transcript_bot_id = transcript.get("bot_id")
            
            # Extract bot_id from download URL if not in transcript object
            transcript_data = transcript.get("data", {})
            download_url = transcript_data.get("download_url", "")
            
            if not transcript_bot_id and download_url:
                # URL format: https://api.recall.ai/api/v1/bot/{bot_id}/transcript/{transcript_id}/
                bot_id_match = re.search(r'/bot/([^/]+)/', download_url)
                if bot_id_match:
                    transcript_bot_id = bot_id_match.group(1)
            
            transcript_info = {
                "transcript_id": transcript.get('id'),
                "bot_id": transcript_bot_id,
                "download_url": download_url[:80] + "..." if len(download_url) > 80 else download_url,
                "matches": transcript_bot_id == bot_id
            }
            transcript_list.append(transcript_info)
            logger.info(f"  Transcript: id={transcript.get('id')}, bot_id={transcript_bot_id}, matches={transcript_bot_id == bot_id}")
            if transcript_bot_id == bot_id:
                transcripts.append(transcript)
        
        # Log to JSON file
        log_bot_filtering_to_json(
            endpoint="/summarization/generate/{bot_id}",
            requested_bot_id=bot_id,
            data={
                "user_id": current_user.id,
                "total_transcripts_returned": len(all_transcripts),
                "transcripts": transcript_list,
                "matching_transcripts_count": len(transcripts),
                "selected_transcript_id": transcripts[0].get('id') if transcripts else None
            }
        )
        
        logger.info(f"✅ Found {len(transcripts)} transcripts matching bot_id {bot_id}")
        
        if not transcripts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transcripts found for bot {bot_id}. The meeting may still be in progress or no transcript was generated."
            )
        
        # Get the most recent transcript for this specific bot
        latest_transcript = transcripts[0]
        logger.info(f"📄 Using transcript id={latest_transcript.get('id')} for bot_id={bot_id}")
        transcript_data = latest_transcript.get("data", {})
        download_url = transcript_data.get("download_url")
        
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcript found but no download URL available for bot {bot_id}"
            )
        
        # Fetch and format the transcript from the download URL
        formatted_result = await recall_service.fetch_and_format_transcript_from_url(download_url)
        
        if not formatted_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch formatted transcript: {formatted_result.get('error', 'Unknown error')}"
            )
        
        # Extract the formatted transcript data
        formatted_transcript = formatted_result.get("formatted_transcript", {})
        continuous_text = formatted_transcript.get("clean_continuous_text", "")
        
        # Fallback to timestamped version if clean version not available
        if not continuous_text:
            continuous_text = formatted_transcript.get("continuous_text", "")
        
        if not continuous_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No continuous text found in formatted transcript"
            )
        
        # For debug: create a preview of the continuous text (first 500 chars)
        transcript_preview = continuous_text[:500] + "..." if len(continuous_text) > 500 else continuous_text
        
        logger.info(f"Generating summary for bot {bot_id} using formatted transcript")
        logger.info(f"Continuous text length: {len(continuous_text)} characters")
        logger.info(f"Transcript preview: {transcript_preview}")
        
        # Generate the summary using our fine-tuned model
        summary = generate_simple_meeting_summary(continuous_text)
        
        # Calculate metrics
        original_words = len(continuous_text.split())
        summary_words = len(summary.split())
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        logger.info(f"Summary generated successfully for bot {bot_id}")
        logger.info(f"Compression: {original_words} words -> {summary_words} words ({compression_ratio:.1%})")
        
        return SummarizationResponse(
            success=True,
            summary=summary,
            metrics={
                "original_words": original_words,
                "summary_words": summary_words,
                "compression_ratio": compression_ratio,
                "model_used": "flan-t5-large"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error generating summary for bot {bot_id}, user {current_user.id}: {e}")
        return SummarizationResponse(
            success=False,
            error=str(e)
        )

