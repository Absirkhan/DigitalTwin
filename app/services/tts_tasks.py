"""
Celery Background Tasks for TTS Synthesis

Provides async TTS generation to avoid blocking API responses.
User submits request → gets job ID immediately → polls for completion.

Benefits:
- Non-blocking UI (user can continue using app)
- Progress tracking
- Automatic caching of results
- Retry logic for transient failures
"""

import logging
import asyncio
from typing import Optional
from celery import Task
from app.core.celery import celery_app
from app.services.tts_service import tts_service
from app.services.tts_cache import tts_cache_service
import soundfile as sf
import io

logger = logging.getLogger(__name__)


class TTSTask(Task):
    """
    Custom Celery task class for TTS synthesis with retry logic.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 2, 'countdown': 5}  # Retry twice with 5s delay
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=TTSTask,
    name="tts.synthesize_speech_async",
    track_started=True,
    time_limit=300  # 5 minutes max
)
def synthesize_speech_async(self, user_id: str, text: str) -> dict:
    """
    Celery task for asynchronous TTS synthesis.

    Args:
        user_id: User identifier
        text: Text to synthesize

    Returns:
        Dictionary with:
            - status: "success" or "error"
            - audio_data: Base64-encoded WAV bytes (if success)
            - cache_key: Redis key for retrieval (if success)
            - error: Error message (if error)
            - elapsed_time: Time taken in seconds
    """
    import time
    start_time = time.time()

    try:
        # Update task state to PROCESSING
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Synthesizing speech...',
                'progress': 0,
                'user_id': user_id,
                'text_preview': text[:50] + '...' if len(text) > 50 else text
            }
        )

        logger.info(f"[Celery TTS] Starting synthesis for user {user_id}")

        # Check cache first
        # Use try-finally to ensure loop is always closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            cached_audio = loop.run_until_complete(
                tts_cache_service.get(user_id, text)
            )

            if cached_audio:
                logger.info(f"[Celery TTS] Cache HIT for user {user_id}")
                elapsed = time.time() - start_time

                # Encode to base64 for JSON serialization
                import base64
                audio_b64 = base64.b64encode(cached_audio).decode('utf-8')

                # Close Redis connection before returning
                try:
                    if tts_cache_service._redis_client:
                        loop.run_until_complete(tts_cache_service._redis_client.close())
                        tts_cache_service._redis_client = None
                except Exception as cleanup_err:
                    logger.debug(f"Redis cleanup warning: {cleanup_err}")

                return {
                    'status': 'success',
                    'audio_data': audio_b64,
                    'cache_hit': True,
                    'elapsed_time': round(elapsed, 2),
                    'message': 'Retrieved from cache'
                }

            # Cache miss - synthesize
            self.update_state(
                state='PROCESSING',
                meta={
                    'status': 'Generating audio...',
                    'progress': 50,
                    'user_id': user_id
                }
            )

            logger.info(f"[Celery TTS] Cache MISS - synthesizing for user {user_id}")

            # Synthesize speech (blocking operation)
            wav_array = loop.run_until_complete(
                tts_service.synthesize_speech(user_id, text)
            )

            # Convert numpy array to WAV bytes
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, wav_array, tts_service.SAMPLE_RATE, format='WAV')
            wav_buffer.seek(0)
            wav_bytes = wav_buffer.getvalue()

            # Store in cache for future requests
            self.update_state(
                state='PROCESSING',
                meta={
                    'status': 'Caching result...',
                    'progress': 90,
                    'user_id': user_id
                }
            )

            try:
                loop.run_until_complete(
                    tts_cache_service.set(user_id, text, wav_bytes)
                )
                logger.info(f"[Celery TTS] Cached result for user {user_id}")
            except Exception as cache_err:
                logger.warning(f"[Celery TTS] Failed to cache: {cache_err}")
                # Don't fail task if caching fails

            # Close Redis connection before closing event loop
            try:
                if tts_cache_service._redis_client:
                    loop.run_until_complete(tts_cache_service._redis_client.close())
                    tts_cache_service._redis_client = None
            except Exception as cleanup_err:
                logger.debug(f"Redis cleanup warning: {cleanup_err}")
        finally:
            # Always close the loop to prevent resource leaks
            loop.close()

        elapsed = time.time() - start_time

        # Encode to base64
        import base64
        audio_b64 = base64.b64encode(wav_bytes).decode('utf-8')

        logger.info(f"[Celery TTS] Synthesis completed for user {user_id} in {elapsed:.2f}s")

        return {
            'status': 'success',
            'audio_data': audio_b64,
            'cache_hit': False,
            'elapsed_time': round(elapsed, 2),
            'message': 'Successfully synthesized'
        }

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"TTS synthesis failed: {str(e)}"
        logger.error(f"[Celery TTS] Error for user {user_id}: {error_msg}")

        return {
            'status': 'error',
            'error': error_msg,
            'elapsed_time': round(elapsed, 2)
        }


@celery_app.task(name="tts.clear_user_cache")
def clear_user_cache_async(user_id: str) -> dict:
    """
    Celery task to clear TTS cache for a user (async).

    Args:
        user_id: User identifier

    Returns:
        Dictionary with cleared_count
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            cleared_count = loop.run_until_complete(
                tts_cache_service.clear_user_cache(user_id)
            )

            logger.info(f"[Celery TTS] Cleared {cleared_count} cache entries for user {user_id}")

            return {
                'status': 'success',
                'cleared_count': cleared_count
            }
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"[Celery TTS] Cache clear failed for user {user_id}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
