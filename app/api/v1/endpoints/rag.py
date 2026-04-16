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
from typing import Optional, List
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


class ResponseCheckRequest(BaseModel):
    """Request schema for bot response simulation."""
    trigger_text: str = Field(..., description="Text that would trigger the bot (e.g., 'Hey Alice, what database are we using?')", min_length=1, max_length=500)
    bot_name: Optional[str] = Field(None, description="Bot name (uses user's bot_name if not specified)")
    response_style: str = Field("helpful", description="Response style (helpful/concise/detailed)")
    simulate_filler: bool = Field(True, description="Whether to simulate filler injection")
    use_cache: bool = Field(False, description="Whether to use cached LLM responses (default False for testing)")


class ResponseCheckChunk(BaseModel):
    """Individual chunk in bot response."""
    chunk_number: int
    text: str
    tts_latency_ms: float
    audio_size_bytes: int
    audio_duration_seconds: float


class ResponseCheckResponse(BaseModel):
    """Response schema for bot response simulation."""
    detected: bool = Field(..., description="Whether bot name was detected in trigger text")
    detection_reason: Optional[str] = Field(None, description="Why bot should/shouldn't respond")
    extracted_query: Optional[str] = Field(None, description="Query extracted from trigger text")
    filler_category: Optional[str] = Field(None, description="Filler category (greeting/question/thinking/goodbye)")
    filler_text: Optional[str] = Field(None, description="Filler text that would be injected")
    filler_latency_ms: Optional[float] = Field(None, description="Filler injection latency")
    rag_context_items: Optional[int] = Field(None, description="Number of RAG context items retrieved")
    rag_retrieval_ms: Optional[float] = Field(None, description="RAG retrieval latency")
    llm_response: Optional[str] = Field(None, description="Full LLM-generated response")
    llm_tokens: Optional[int] = Field(None, description="Number of tokens generated")
    llm_latency_ms: Optional[float] = Field(None, description="LLM generation latency")
    response_chunks: Optional[List[ResponseCheckChunk]] = Field(None, description="Simulated TTS chunks")
    total_pipeline_ms: Optional[float] = Field(None, description="Total pipeline latency")
    perceived_latency_ms: Optional[float] = Field(None, description="Perceived latency (time to first audio)")
    cached: bool = Field(False, description="Whether response was cached")


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


@router.post("/response-check", response_model=ResponseCheckResponse)
async def check_bot_response(
    request: ResponseCheckRequest,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Test endpoint: Simulate bot response without joining a meeting.

    This endpoint simulates the full bot response pipeline:
    1. Bot name detection
    2. Query extraction
    3. Filler analysis (category detection)
    4. RAG context retrieval
    5. LLM response generation
    6. TTS chunking simulation (no actual audio injection)

    **Use cases:**
    - Test if bot name detection works for different phrasings
    - Check what context RAG retrieves for a query
    - Preview LLM responses before going live
    - Measure pipeline latency without joining meetings
    - Debug filler injection logic

    **Example requests:**

    ```json
    {
      "trigger_text": "Hey Alice, what database are we using?",
      "bot_name": "Alice",
      "simulate_filler": true
    }
    ```

    ```json
    {
      "trigger_text": "Bob, can you summarize the last meeting?",
      "response_style": "concise"
    }
    ```

    Args:
        request: Response check request
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        Simulated bot response with full pipeline metrics
    """
    import time
    import asyncio
    from app.services.bot_speaking_engine import get_bot_speaking_engine
    from app.services.filler_audio_injector import filler_audio_injector
    from app.services.piper_tts_service import piper_tts_service

    # Import RAG pipeline and streaming
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "rag_module"))
    from rag_module.rag.streaming_buffer import StreamingBuffer, stream_llm_to_chunks

    start_time = time.time()

    # === VERBOSE LOGGING: REQUEST RECEIVED ===
    print("\n" + "="*80)
    print("🧪 BOT RESPONSE CHECK - REQUEST RECEIVED")
    print("="*80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"User ID: {current_user.id}")
    print(f"User Email: {current_user.email}")
    print(f"Trigger Text: '{request.trigger_text}'")
    print(f"Bot Name (override): {request.bot_name or 'None (using user profile)'}")
    print(f"Simulate Filler: {request.simulate_filler}")
    print(f"Use Cache: {request.use_cache}")
    print(f"Response Style: {request.response_style}")
    print("="*80 + "\n")

    try:
        # Get bot name (use user's bot_name if not specified)
        bot_name = request.bot_name or current_user.bot_name or "Assistant"

        # Get user info for RAG
        user_name = current_user.full_name or current_user.email.split('@')[0]

        logger.info(
            f"🧪 Response check: user={current_user.id}, "
            f"bot_name='{bot_name}', trigger='{request.trigger_text[:50]}'"
        )

        print(f"🤖 Active Bot Name: '{bot_name}'")
        print(f"👤 User Name: '{user_name}'\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 1: Bot Name Detection
        # ═══════════════════════════════════════════════════════════
        print("="*80)
        print("🎯 STAGE 1: BOT NAME DETECTION")
        print("="*80)

        engine = get_bot_speaking_engine()
        should_respond, reason = engine.should_respond(
            request.trigger_text,
            "TestSpeaker",
            bot_name
        )

        print(f"Trigger Text: '{request.trigger_text}'")
        print(f"Bot Name: '{bot_name}'")
        print(f"Should Respond: {should_respond}")
        print(f"Reason: {reason}")
        print("="*80 + "\n")

        if not should_respond:
            # Bot name not detected
            print("❌ BOT NOT DETECTED - Stopping pipeline\n")
            return ResponseCheckResponse(
                detected=False,
                detection_reason=reason,
                extracted_query=None,
                filler_category=None,
                filler_text=None,
                llm_response=None
            )

        print("✅ BOT DETECTED - Continuing pipeline\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 2: Query Extraction
        # ═══════════════════════════════════════════════════════════
        print("="*80)
        print("🔍 STAGE 2: QUERY EXTRACTION")
        print("="*80)

        query = engine.extract_query_from_address(request.trigger_text, bot_name)

        print(f"Original Text: '{request.trigger_text}'")
        print(f"Bot Name Removed: '{bot_name}'")
        print(f"Extracted Query: '{query}'")
        print("="*80 + "\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 3: Filler Analysis (if enabled)
        # ═══════════════════════════════════════════════════════════
        filler_category = None
        filler_text = None
        filler_latency_ms = None

        if request.simulate_filler:
            print("="*80)
            print("💬 STAGE 3: FILLER ANALYSIS")
            print("="*80)

            filler_start = time.time()
            query_analysis = filler_audio_injector.analyze_query_context(query)
            filler_category = query_analysis.get('category', 'unknown')

            # Get filler text based on category
            if filler_category == 'greeting':
                filler_text = "Hello!"
            elif filler_category == 'goodbye':
                filler_text = "Goodbye!"
            elif filler_category == 'question':
                filler_text = "Let me think..."
            elif filler_category == 'statement':
                filler_text = "Hmm..."
            else:
                filler_text = "Uh..."

            filler_latency_ms = (time.time() - filler_start) * 1000

            print(f"Query: '{query}'")
            print(f"Category: {filler_category}")
            print(f"Filler Text: \"{filler_text}\"")
            print(f"Analysis Time: {filler_latency_ms:.1f}ms")
            print(f"Query Analysis: {query_analysis}")
            print("="*80 + "\n")
        else:
            print("⏭️ STAGE 3: FILLER SKIPPED (simulate_filler=False)\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 4: Check for Greeting/Goodbye (Skip RAG/LLM)
        # ═══════════════════════════════════════════════════════════
        if filler_category in ['greeting', 'goodbye']:
            print("="*80)
            print(f"🎭 STAGE 4: TEMPLATE RESPONSE ({filler_category.upper()})")
            print("="*80)
            print("⏭️ Skipping RAG and LLM (using template response)")

            # Use template response
            import random
            if filler_category == 'greeting':
                template_responses = [
                    "Hello! How can I help you?",
                    "Hi there! What can I do for you?",
                    "Hey! What do you need?",
                ]
            else:
                template_responses = [
                    "Goodbye! Have a great day!",
                    "See you later! Take care!",
                    "Bye! Talk to you soon!",
                ]

            llm_response = random.choice(template_responses)
            llm_tokens = len(llm_response.split())
            llm_latency_ms = 5.0  # Template is instant

            print(f"Template Options: {template_responses}")
            print(f"Selected: \"{llm_response}\"")
            print(f"Tokens: {llm_tokens}")
            print(f"Latency: {llm_latency_ms:.0f}ms (instant)")

            # Simulate single TTS chunk
            tts_start = time.time()
            simulated_audio_size = len(llm_response) * 100  # Rough estimate
            tts_latency = 50.0  # Estimated
            audio_duration = len(llm_response) / 15.0  # ~15 chars/sec speech

            response_chunks = [
                ResponseCheckChunk(
                    chunk_number=1,
                    text=llm_response,
                    tts_latency_ms=tts_latency,
                    audio_size_bytes=simulated_audio_size,
                    audio_duration_seconds=audio_duration
                )
            ]

            total_time = (time.time() - start_time) * 1000
            perceived_latency = filler_latency_ms or total_time

            print(f"\n✅ TEMPLATE RESPONSE COMPLETE")
            print(f"Total Time: {total_time:.0f}ms")
            print(f"Perceived Latency: {perceived_latency:.0f}ms")
            print("="*80 + "\n")

            return ResponseCheckResponse(
                detected=True,
                detection_reason=reason,
                extracted_query=query,
                filler_category=filler_category,
                filler_text=filler_text,
                filler_latency_ms=filler_latency_ms,
                rag_context_items=0,
                rag_retrieval_ms=0.0,
                llm_response=llm_response,
                llm_tokens=llm_tokens,
                llm_latency_ms=llm_latency_ms,
                response_chunks=response_chunks,
                total_pipeline_ms=total_time,
                perceived_latency_ms=perceived_latency,
                cached=False
            )

        # ═══════════════════════════════════════════════════════════
        # STAGE 5: RAG Context Retrieval
        # ═══════════════════════════════════════════════════════════
        rag_start = time.time()

        # Access the pipeline directly
        pipeline = rag_service._pipeline

        # Get prompt with RAG context
        prompt_result = await asyncio.get_event_loop().run_in_executor(
            None,
            pipeline.process_message,
            str(current_user.id),
            query
        )

        rag_retrieval_ms = (time.time() - rag_start) * 1000
        rag_context_items = prompt_result.get('num_results_retrieved', 0)

        # === VERBOSE LOGGING: RAG SOURCES ===
        print("\n" + "="*80)
        print("🔍 RAG CONTEXT RETRIEVAL - SOURCES")
        print("="*80)
        print(f"User ID: {current_user.id}")
        print(f"Query: '{query}'")
        print(f"Context Items Retrieved: {rag_context_items}")
        print(f"Retrieval Time: {rag_retrieval_ms:.0f}ms")

        if rag_context_items > 0:
            retrieved_context = prompt_result.get('retrieved_context', '')
            print(f"\n📚 RETRIEVED CONTEXT:")
            print("-" * 80)
            print(retrieved_context)
            print("-" * 80)
        else:
            print("\n⚠️ NO CONTEXT RETRIEVED (empty knowledge base or no relevant matches)")

        print("\n🎯 FULL PROMPT SENT TO LLM:")
        print("-" * 80)
        print(prompt_result.get('prompt', 'N/A'))
        print("-" * 80)
        print("="*80 + "\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 6: LLM Response Generation (Streaming)
        # ═══════════════════════════════════════════════════════════
        llm_start = time.time()

        # Get LLM generator
        llm_generator = pipeline.llm_generator

        # Generate with streaming
        llm_stream_sync = llm_generator.generate_response_stream(
            prompt=prompt_result['prompt'],
            max_tokens=50,  # Match optimized pipeline
            use_cache=request.use_cache
        )

        # Convert sync to async
        async def async_wrapper(sync_gen):
            for item in sync_gen:
                yield item
                await asyncio.sleep(0)

        llm_stream = async_wrapper(llm_stream_sync)

        # Wrap with chunking buffer
        buffer = StreamingBuffer()
        chunked_stream = stream_llm_to_chunks(llm_stream, buffer)

        # Collect chunks
        llm_response_parts = []
        response_chunks = []
        chunk_count = 0
        total_tokens = 0
        cached = False

        async for chunk_dict in chunked_stream:
            if chunk_dict.get('type') == 'chunk':
                chunk_count += 1
                chunk_text = chunk_dict.get('content', '')
                llm_response_parts.append(chunk_text)

                # Simulate TTS for chunk
                tts_start = time.time()

                # Estimate audio size (rough approximation)
                # Piper typically generates ~20KB per sentence
                simulated_audio_size = len(chunk_text) * 150

                # Estimate TTS latency (~50-150ms per chunk)
                tts_latency = 50 + (len(chunk_text) * 2)

                # Estimate audio duration (~15 chars per second of speech)
                audio_duration = len(chunk_text) / 15.0

                response_chunks.append(
                    ResponseCheckChunk(
                        chunk_number=chunk_count,
                        text=chunk_text,
                        tts_latency_ms=tts_latency,
                        audio_size_bytes=simulated_audio_size,
                        audio_duration_seconds=audio_duration
                    )
                )

            elif chunk_dict.get('type') == 'done':
                stats = chunk_dict.get('stats', {})
                total_tokens = stats.get('total_tokens_processed', 0)
                cached = chunk_dict.get('cached', False)

        llm_latency_ms = (time.time() - llm_start) * 1000
        llm_response = ' '.join(llm_response_parts).strip()

        # === VERBOSE LOGGING: LLM RESPONSE ===
        print("\n" + "="*80)
        print("🤖 LLM RESPONSE GENERATION - RESULTS")
        print("="*80)
        print(f"Model: Qwen2.5-0.5B-Instruct (Q4_K_M)")
        print(f"Tokens Generated: {total_tokens}")
        print(f"Generation Time: {llm_latency_ms:.0f}ms")
        print(f"Tokens/Second: {(total_tokens / (llm_latency_ms / 1000)):.1f}")
        print(f"Cached: {cached}")
        print(f"Chunks: {chunk_count}")

        print(f"\n💭 GENERATED RESPONSE:")
        print("-" * 80)
        print(llm_response)
        print("-" * 80)

        if response_chunks:
            print(f"\n📝 RESPONSE CHUNKS ({len(response_chunks)}):")
            for chunk in response_chunks:
                print(f"  Chunk {chunk.chunk_number}: \"{chunk.text}\" ({chunk.audio_size_bytes} bytes, {chunk.audio_duration_seconds:.1f}s)")

        print("="*80 + "\n")

        # ═══════════════════════════════════════════════════════════
        # STAGE 7: Calculate Metrics
        # ═══════════════════════════════════════════════════════════
        total_time = (time.time() - start_time) * 1000

        # Perceived latency = filler injection time (or first chunk time if no filler)
        if request.simulate_filler and filler_latency_ms:
            perceived_latency = filler_latency_ms
        else:
            # If no filler, user waits until first TTS chunk completes
            first_chunk_tts = response_chunks[0].tts_latency_ms if response_chunks else 0
            perceived_latency = rag_retrieval_ms + llm_latency_ms + first_chunk_tts

        # === VERBOSE LOGGING: FINAL SUMMARY ===
        print("\n" + "="*80)
        print("✅ BOT RESPONSE CHECK - COMPLETE")
        print("="*80)
        print(f"Total Pipeline Time: {total_time:.0f}ms")
        print(f"Perceived Latency: {perceived_latency:.0f}ms")
        print(f"\nBreakdown:")
        print(f"  - Filler: {filler_latency_ms:.0f}ms" if filler_latency_ms else "  - Filler: SKIPPED")
        print(f"  - RAG Retrieval: {rag_retrieval_ms:.0f}ms ({rag_context_items} items)")
        print(f"  - LLM Generation: {llm_latency_ms:.0f}ms ({total_tokens} tokens) {'[CACHED]' if cached else ''}")
        print(f"\nFinal Response: \"{llm_response}\"")
        print("="*80 + "\n")

        return ResponseCheckResponse(
            detected=True,
            detection_reason=reason,
            extracted_query=query,
            filler_category=filler_category,
            filler_text=filler_text,
            filler_latency_ms=filler_latency_ms,
            rag_context_items=rag_context_items,
            rag_retrieval_ms=rag_retrieval_ms,
            llm_response=llm_response,
            llm_tokens=total_tokens,
            llm_latency_ms=llm_latency_ms,
            response_chunks=response_chunks,
            total_pipeline_ms=total_time,
            perceived_latency_ms=perceived_latency,
            cached=cached
        )

    except RuntimeError as e:
        # RAG service not initialized
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error in response check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check response: {str(e)}"
        )
