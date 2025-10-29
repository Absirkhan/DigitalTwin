"""
Summarization endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

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


class SummarizationRequest(BaseModel):
    pass  # No bot_id needed, will get latest bot automatically


class BotSummarizationRequest(BaseModel):
    bot_id: str  # UUID string


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
        
        logger.info(f"Generating summary for bot {bot_id} for user {current_user.id}")
        
        # Get the formatted transcript from recall service
        transcripts_result = await recall_service.list_transcripts(bot_id=bot_id)
        
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
        logger.error(f"Error generating summary for bot {bot_id}, user {current_user.id}: {e}")
        return SummarizationResponse(
            success=False,
            error=str(e)
        )

