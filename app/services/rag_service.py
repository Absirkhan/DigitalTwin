"""
RAG Service - Voice Assistant Context Retrieval with LLM Response Generation

Provides intelligent context-aware response generation using:
- FAISS vector search for retrieving relevant past conversations
- Local LLM (Qwen2.5-0.5B) for dynamic response generation
- Redis caching for instant repeated query responses
- Per-user isolation and profile management

This service wraps the standalone rag_module and integrates it with the main application.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)

# Add rag_module to Python path
RAG_MODULE_PATH = Path(__file__).parent.parent.parent / "rag_module"
if str(RAG_MODULE_PATH) not in sys.path:
    sys.path.insert(0, str(RAG_MODULE_PATH))


class RAGService:
    """
    Singleton service for RAG (Retrieval-Augmented Generation) operations.

    Integrates with:
    - RAG Pipeline (FAISS vector search, user profiling, session memory)
    - LLM Generator (Qwen2.5-0.5B with streaming and caching)
    - Recall.ai service (transcript retrieval)

    Pre-warms LLM model on application startup to eliminate first-request delay.
    """

    _instance: Optional['RAGService'] = None
    _initialized = False
    _pipeline = None
    _llm_available = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize service (model loaded lazily on first use)."""
        if not hasattr(self, '_initialized_instance'):
            self._initialized_instance = True
            logger.info("RAG service initialized (LLM will load on first use)")

    async def initialize(self):
        """
        Pre-warm the RAG pipeline and LLM model.

        Called during application startup to eliminate first-request delay.
        This loads the LLM model into memory (~30s on first load).
        """
        if self._initialized:
            logger.info("RAG service already initialized")
            return

        try:
            logger.info("Initializing RAG pipeline and LLM model...")
            logger.info(f"RAG module path: {RAG_MODULE_PATH}")

            # Import RAG modules
            from rag.pipeline import RAGPipeline

            # Import config from rag_module
            sys.path.insert(0, str(RAG_MODULE_PATH))
            from config import RAGConfig

            # Log model configuration for debugging
            model_path = RAGConfig.MODEL_PATH
            logger.info(f"Model path from config: {model_path}")
            logger.info(f"Model file exists: {Path(model_path).exists()}")

            if not Path(model_path).exists():
                logger.error(f"❌ Model file not found: {model_path}")
                logger.error("   RAG/LLM features will be disabled")
                self._initialized = False
                return

            # Initialize pipeline with LLM enabled
            base_path = str(RAG_MODULE_PATH / "data" / "users")
            logger.info(f"User data path: {base_path}")

            logger.info("Loading RAG pipeline (this may take 10-30s)...")
            self._pipeline = RAGPipeline(base_path=base_path, enable_llm=True)

            # Check if LLM is available
            self._llm_available = self._pipeline.llm_generator is not None

            if self._llm_available:
                logger.info("✅ RAG pipeline initialized with LLM support")

                # Pre-warm the model by generating a test response
                logger.info("Pre-warming LLM model (this may take 10-30s on first load)...")

                # Use asyncio.wait_for with timeout to prevent hanging
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            self._prewarm_llm
                        ),
                        timeout=30.0  # 30 second timeout (model already loaded)
                    )
                    logger.info("✅ LLM model pre-warmed and ready")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ LLM pre-warming timed out after 30s")
                    logger.warning("   First query may be slower than expected")
                    # Still mark as initialized since pipeline is loaded
                    pass
            else:
                logger.warning("⚠️ RAG pipeline initialized WITHOUT LLM support")
                if self._pipeline.llm_generator is None:
                    logger.warning("   LLM generator is None - check model file and llama-cpp-python installation")

            self._initialized = True
            logger.info("✅ RAG service initialization complete")

        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG service: {e}", exc_info=True)
            logger.error("   RAG/LLM features will be disabled")
            # Don't raise - allow app to start even if RAG fails
            self._initialized = False
            self._llm_available = False

    def _prewarm_llm(self):
        """Synchronous pre-warming helper (runs in thread pool)."""
        try:
            # Generate a tiny test response to warm up the model
            result = self._pipeline.generate_response(
                user_id="__prewarm__",
                message="test",
                max_tokens=5,
                use_cache=False,
                auto_store=False
            )
            logger.info(f"Pre-warm complete: {result.get('llm_latency_ms', 0):.0f}ms")
        except Exception as e:
            logger.warning(f"Pre-warm failed (non-critical): {e}")

    async def process_user_query(
        self,
        user_id: str,
        message: str,
        user_name: Optional[str] = None,
        bot_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        auto_store: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user query with RAG context retrieval and LLM response generation.

        Args:
            user_id: User ID (for context isolation)
            message: User's query message
            user_name: User's full name (for prompt context)
            bot_name: Bot's name in meetings (for prompt context)
            max_tokens: Maximum tokens to generate (default: 200)
            use_cache: Whether to use cached responses (default: True)
            auto_store: Whether to store this exchange in RAG (default: True)

        Returns:
            Dict with:
                - response: Generated response text
                - retrieval_latency_ms: Context retrieval time
                - llm_latency_ms: LLM generation time
                - total_latency_ms: Total processing time
                - tokens_generated: Number of tokens generated
                - cached: Whether response was cached
                - context_items: Number of context items retrieved
        """
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")

        if not self._llm_available:
            raise RuntimeError("LLM not available. Check model installation.")

        try:
            # Run in thread pool to avoid blocking async event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._process_query_sync,
                user_id,
                message,
                user_name,
                bot_name,
                max_tokens,
                use_cache,
                auto_store
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error processing user query: {e}", exc_info=True)
            raise

    def _process_query_sync(
        self,
        user_id: str,
        message: str,
        user_name: Optional[str],
        bot_name: Optional[str],
        max_tokens: Optional[int],
        use_cache: bool,
        auto_store: bool
    ) -> Dict[str, Any]:
        """Synchronous query processing (runs in thread pool)."""

        # Build enhanced prompt with user name context
        enhanced_message = message
        if user_name or bot_name:
            context_prefix = "User Context:\n"
            if bot_name:
                context_prefix += f"- Your name in meetings: {bot_name}\n"
            if user_name:
                context_prefix += f"- User's name: {user_name}\n"
            context_prefix += f"\nUser Query: {message}"
            enhanced_message = context_prefix

        # Generate response with RAG context
        result = self._pipeline.generate_response(
            user_id=user_id,
            message=enhanced_message,
            max_tokens=max_tokens,
            use_cache=use_cache,
            auto_store=auto_store
        )

        return result

    async def process_user_query_stream(
        self,
        user_id: str,
        message: str,
        user_name: Optional[str] = None,
        bot_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        auto_store: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user query with streaming response generation.

        Yields chunks as they are generated for better UX.

        Args:
            Same as process_user_query()

        Yields:
            Dicts with:
                - type: "context" | "token" | "done" | "error"
                - content: The content (depends on type)
                - Additional metadata
        """
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")

        if not self._llm_available:
            raise RuntimeError("LLM not available. Check model installation.")

        try:
            # Build enhanced message with user context
            enhanced_message = message
            if user_name or bot_name:
                context_prefix = "User Context:\n"
                if bot_name:
                    context_prefix += f"- Your name in meetings: {bot_name}\n"
                if user_name:
                    context_prefix += f"- User's name: {user_name}\n"
                context_prefix += f"\nUser Query: {message}"
                enhanced_message = context_prefix

            # Stream response generation
            for chunk in self._pipeline.generate_response_stream(
                user_id=user_id,
                message=enhanced_message,
                max_tokens=max_tokens,
                use_cache=use_cache,
                auto_store=auto_store
            ):
                yield chunk

        except Exception as e:
            logger.error(f"❌ Error in streaming query: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}

    async def store_meeting_transcript(
        self,
        user_id: str,
        bot_id: str,
        user_name: Optional[str] = None,
        bot_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch meeting transcript from formatted endpoint and store in RAG.

        Stores each speaker's dialogue as a separate exchange for fine-grained
        context retrieval.

        Args:
            user_id: User ID (for context isolation)
            bot_id: Recall.ai bot ID
            user_name: User's full name
            bot_name: Bot's name in the meeting

        Returns:
            Dict with:
                - success: Whether storage succeeded
                - total_exchanges_stored: Number of exchanges stored
                - speakers: List of unique speakers found
                - error: Error message (if failed)
        """
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")

        try:
            # Import HTTP client for internal API call
            import httpx
            from app.core.database import AsyncSessionLocal
            from app.models.bot import Bot

            logger.info(f"Fetching formatted transcript for bot {bot_id}...")

            # Get bot from database to verify user ownership
            db = AsyncSessionLocal()
            try:
                from sqlalchemy import select
                result = await db.execute(
                    select(Bot).filter(Bot.bot_id == bot_id)
                )
                bot = result.scalar_one_or_none()

                if not bot or bot.user_id != int(user_id):
                    logger.error(f"Bot {bot_id} not found or doesn't belong to user {user_id}")
                    return {
                        "success": False,
                        "error": "Bot not found or access denied",
                        "total_exchanges_stored": 0,
                        "speakers": []
                    }

                # Get user's email for JWT token (needed for internal API call)
                from app.models.user import User
                result = await db.execute(
                    select(User).filter(User.id == int(user_id))
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.error(f"User {user_id} not found")
                    return {
                        "success": False,
                        "error": "User not found",
                        "total_exchanges_stored": 0,
                        "speakers": []
                    }

                # Create JWT token with correct format (sub = email)
                from app.services.auth import create_access_token
                access_token = create_access_token(data={"sub": user.email})

            finally:
                await db.close()

            # Call the formatted transcript endpoint (internal API call)
            base_url = "http://localhost:8000"  # Internal call
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/api/v1/meetings/bot/{bot_id}/transcript/formatted",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if response.status_code != 200:
                    error_msg = f"Failed to fetch transcript: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "total_exchanges_stored": 0,
                        "speakers": []
                    }

                data = response.json()

            # Extract speaker dialogues from formatted transcript
            formatted_transcript = data.get("formatted_transcript", {})
            speaker_dialogues = formatted_transcript.get("speaker_dialogues", [])

            if not speaker_dialogues:
                return {
                    "success": False,
                    "error": "No speaker dialogues found in transcript",
                    "total_exchanges_stored": 0,
                    "speakers": []
                }

            # Convert to speaker segments format
            speaker_segments = []
            speakers_set = set()

            for dialogue in speaker_dialogues:
                speaker = dialogue.get("speaker", "Unknown")
                text = dialogue.get("text", "").strip()

                if not text:
                    continue

                speakers_set.add(speaker)
                speaker_segments.append({
                    "speaker": speaker,
                    "text": text
                })

            # Store each segment in RAG
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_segments_sync,
                user_id,
                speaker_segments
            )

            exchanges_stored = len(speaker_segments)

            logger.info(
                f"✅ Stored {exchanges_stored} transcript exchanges for user {user_id} "
                f"({len(speakers_set)} speakers)"
            )

            return {
                "success": True,
                "total_exchanges_stored": exchanges_stored,
                "speakers": list(speakers_set)
            }

        except Exception as e:
            logger.error(f"❌ Error storing transcript in RAG: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "total_exchanges_stored": 0,
                "speakers": []
            }

    def _store_segments_sync(self, user_id: str, segments: List[Dict[str, str]]):
        """
        Synchronous segment storage (runs in thread pool).

        Stores meeting transcript segments as searchable exchanges.
        Both user_message and assistant_response contain the full speaker text
        for better retrieval (since these are transcripts, not Q&A pairs).
        """
        for segment in segments:
            speaker = segment["speaker"]
            text = segment["text"]

            # Store the full speaker dialogue in both fields for maximum retrieval relevance
            # Format: "Speaker: Their actual words"
            formatted_text = f"{speaker}: {text}"

            self._pipeline.store_exchange(
                user_id=user_id,
                user_message=formatted_text,
                assistant_response=formatted_text  # Store actual content, not "context"
            )

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics and profile information."""
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")

        try:
            stats = await asyncio.get_event_loop().run_in_executor(
                None,
                self._pipeline.get_user_stats,
                user_id
            )
            return stats
        except Exception as e:
            logger.error(f"❌ Error getting user stats: {e}", exc_info=True)
            raise

    async def get_cache_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics.

        Args:
            user_id: Optional user ID (not used currently, cache is global)

        Returns:
            Dict with cache statistics
        """
        if not self._initialized or not self._llm_available:
            return {
                "error": "RAG/LLM not initialized",
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0
            }

        try:
            cache = self._pipeline.llm_generator.cache
            stats = cache.get_cache_stats()
            return stats
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}", exc_info=True)
            return {
                "error": str(e),
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0
            }

    async def clear_user_cache(self, user_id: str) -> Dict[str, Any]:
        """
        Clear cached responses for a user.

        Note: Current implementation has global cache (not per-user).
        This clears the entire cache.

        Args:
            user_id: User ID (for future per-user cache support)

        Returns:
            Dict with success status
        """
        if not self._initialized or not self._llm_available:
            return {"success": False, "error": "RAG/LLM not initialized"}

        try:
            cache = self._pipeline.llm_generator.cache
            cleared = cache.clear_cache()

            logger.info(f"Cache cleared for user {user_id}: {cleared} entries removed")

            return {
                "success": True,
                "message": f"Cleared {cleared} cached responses",
                "entries_cleared": cleared
            }
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def end_session(self, user_id: str) -> Dict[str, Any]:
        """
        End user session (clear session memory, keep long-term storage).

        Args:
            user_id: User ID

        Returns:
            Dict with session info
        """
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._pipeline.end_session,
                user_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Error ending session: {e}", exc_info=True)
            raise


# Global singleton instance
rag_service = RAGService()
