"""
RAG (Retrieval-Augmented Generation) API Endpoints

Provides endpoints for intelligent context-aware AI responses using:
- Vector search for retrieving relevant past conversations
- Local LLM for dynamic response generation
- Redis caching for instant repeated responses
- Per-user isolation and profile management

All endpoints require JWT authentication.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.bot import Bot
from app.services.auth import get_current_user_bearer
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== REQUEST/RESPONSE SCHEMAS =====

class QueryRequest(BaseModel):
    """Request schema for RAG query."""
    message: str = Field(..., description="User's query message", min_length=1, max_length=1000)
    use_cache: bool = Field(True, description="Whether to use cached responses")
    auto_store: bool = Field(True, description="Whether to store this exchange in RAG")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate (default: 500)", ge=10, le=1000)


class QueryResponse(BaseModel):
    """Response schema for RAG query."""
    response: str = Field(..., description="Generated response text")
    retrieval_latency_ms: float = Field(..., description="Context retrieval time in milliseconds")
    llm_latency_ms: float = Field(..., description="LLM generation time in milliseconds")
    total_latency_ms: float = Field(..., description="Total processing time in milliseconds")
    tokens_generated: int = Field(..., description="Number of tokens generated")
    cached: bool = Field(..., description="Whether response was cached")
    context_items: int = Field(..., description="Number of context items retrieved")


class UserStatsResponse(BaseModel):
    """Response schema for user statistics."""
    user_id: str
    total_exchanges: int
    session_messages: int
    profile: dict


class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""
    hits: int
    misses: int
    hit_rate: float
    total_cached_responses: int


class TranscriptStorageResponse(BaseModel):
    """Response schema for transcript storage."""
    success: bool
    total_exchanges_stored: int
    speakers: list
    error: Optional[str] = None


class SessionEndResponse(BaseModel):
    """Response schema for session end."""
    success: bool
    session_cleared: bool
    messages_in_session: int
    total_exchanges_stored: int


# ===== ENDPOINTS =====

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Query the RAG system with a user message and get an AI-generated response.

    This endpoint:
    1. Retrieves relevant context from past conversations (FAISS vector search)
    2. Generates a response using the local LLM (Qwen2.5-0.5B)
    3. Caches the response for instant future retrieval
    4. Optionally stores the exchange in RAG for future context

    **Performance**:
    - First request: ~3-4s (LLM generation)
    - Cached responses: <50ms (instant)
    - Expected cache hit rate: 30-40%

    **User Context**:
    - User's name and bot name are automatically included in the prompt
    - Retrieved context shows past meeting transcripts and conversations
    - Each user has isolated context (cannot see other users' data)

    Args:
        request: Query request with message and options
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        Generated response with latency metrics
    """
    try:
        # Get user name information for prompt context
        user_name = current_user.full_name or current_user.email.split('@')[0]
        bot_name = current_user.bot_name  # May be None

        # Process query with RAG
        result = await rag_service.process_user_query(
            user_id=str(current_user.id),
            message=request.message,
            user_name=user_name,
            bot_name=bot_name,
            max_tokens=request.max_tokens,
            use_cache=request.use_cache,
            auto_store=request.auto_store
        )

        # Extract context items count from result
        context_items = result.get('num_results_retrieved', 0)

        return QueryResponse(
            response=result['response'],
            retrieval_latency_ms=result['retrieval_latency_ms'],
            llm_latency_ms=result['llm_latency_ms'],
            total_latency_ms=result['total_latency_ms'],
            tokens_generated=result['tokens_generated'],
            cached=result['cached'],
            context_items=context_items
        )

    except RuntimeError as e:
        # RAG service not initialized
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error processing RAG query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get user statistics and profile information.

    Returns:
        - Total number of exchanges stored in RAG
        - Number of messages in current session
        - User profile (speaking style, preferences, etc.)
    """
    try:
        stats = await rag_service.get_user_stats(str(current_user.id))
        return UserStatsResponse(**stats)

    except Exception as e:
        logger.error(f"❌ Error getting user stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get cache statistics for LLM responses.

    Returns:
        - Cache hits and misses
        - Hit rate percentage
        - Total cached responses

    Note: Cache is currently global (not per-user).
    """
    try:
        stats = await rag_service.get_cache_stats(str(current_user.id))

        # Handle error case
        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=stats["error"]
            )

        return CacheStatsResponse(
            hits=stats.get('hits', 0),
            misses=stats.get('misses', 0),
            hit_rate=stats.get('hit_rate', 0.0),
            total_cached_responses=stats.get('cached_responses', 0)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Clear cached LLM responses.

    Note: Currently clears the entire cache (not per-user).
    Future versions will support per-user cache clearing.

    Returns:
        Success status and number of entries cleared
    """
    try:
        result = await rag_service.clear_user_cache(str(current_user.id))

        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', 'Failed to clear cache')
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.post("/session/end", response_model=SessionEndResponse)
async def end_session(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    End the current RAG session.

    This clears the session memory (last 6 messages) but keeps all
    long-term stored exchanges intact.

    Use this when:
    - User logs out
    - Starting a new conversation context
    - Resetting recent conversation history

    Returns:
        Session information and storage status
    """
    try:
        result = await rag_service.end_session(str(current_user.id))
        return SessionEndResponse(**result)

    except Exception as e:
        logger.error(f"❌ Error ending session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.post("/store-transcript/{meeting_id}", response_model=TranscriptStorageResponse)
async def store_meeting_transcript(
    meeting_id: int,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Manually store a meeting transcript in RAG.

    This endpoint allows users to manually trigger transcript storage
    for a specific meeting. Normally, transcripts are automatically stored
    when meetings complete.

    The transcript is fetched from Recall.ai and each speaker's dialogue
    is stored as a separate exchange for fine-grained context retrieval.

    Args:
        meeting_id: ID of the meeting
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        Storage result with number of exchanges stored and speakers found
    """
    try:
        # Verify meeting belongs to user
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == current_user.id
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        # Get associated bot
        bot = db.query(Bot).filter(Bot.meeting_id == meeting_id).first()

        if not bot or not bot.bot_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No bot associated with this meeting"
            )

        # Get user name information
        user_name = current_user.full_name or current_user.email.split('@')[0]
        bot_name = current_user.bot_name  # May be None

        # Store transcript in RAG
        result = await rag_service.store_meeting_transcript(
            user_id=str(current_user.id),
            bot_id=bot.bot_id,
            user_name=user_name,
            bot_name=bot_name
        )

        return TranscriptStorageResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error storing transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store transcript: {str(e)}"
        )
