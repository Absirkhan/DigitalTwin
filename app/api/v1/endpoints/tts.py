"""
Text-to-Speech (TTS) endpoints for voice cloning with NeuTTS Nano

Provides endpoints for:
- Uploading voice samples to create user voice profiles
- Checking voice profile status
- Synthesizing speech with user's cloned voice
- Deleting voice profiles
"""
import os
import tempfile
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import soundfile as sf
import io

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user_bearer
from app.services.tts_service import tts_service
from app.services.tts_cache import tts_cache_service
from app.services.tts_tasks import synthesize_speech_async
from celery.result import AsyncResult

logger = logging.getLogger(__name__)

router = APIRouter()

# File upload constraints
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3"}


@router.post("/upload-voice")
async def upload_voice(
    audio_file: UploadFile = File(..., description="Voice sample audio file (.wav or .mp3, max 10MB)"),
    ref_text: str = Form(..., description="Transcript of what was said in the audio"),
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Upload a voice sample to create or update user's voice profile.

    This endpoint:
    1. Validates the uploaded audio file (format and size)
    2. Encodes the voice using NeuTTS Nano
    3. Saves the voice profile for future use
    4. Updates user's has_voice_profile flag

    The voice profile is used to synthesize speech in the user's voice
    during automated meeting responses.

    Args:
        audio_file: Audio file containing 10-15 seconds of user's voice
        ref_text: Exact transcript of what was said in the audio (required for quality)
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        Success message confirming voice profile was saved
    """
    try:
        # Validate file extension
        file_ext = os.path.splitext(audio_file.filename)[1].lower()
        if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Allowed formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
            )

        # Read file content
        file_content = await audio_file.read()

        # Validate file size
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
            )

        # Validate ref_text is not empty
        if not ref_text or not ref_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference text (transcript) is required and cannot be empty"
            )

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        try:
            # Encode voice and save profile
            logger.info(f"Processing voice upload for user {current_user.id}")
            await tts_service.encode_and_save_voice(
                user_id=str(current_user.id),
                audio_file_path=temp_path,
                ref_text=ref_text.strip()
            )

            # Update user's has_voice_profile flag
            user = db.query(User).filter(User.id == current_user.id).first()
            if user:
                user.has_voice_profile = True
                db.commit()

            logger.info(f"Voice profile created successfully for user {current_user.id}")

            return {
                "success": True,
                "message": "Voice profile saved successfully"
            }

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice upload failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice upload failed: {str(e)}"
        )


@router.get("/voice-status")
async def get_voice_status(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Check if the current user has a voice profile.

    Returns:
        has_voice_profile: Boolean indicating if voice profile exists
    """
    has_profile = tts_service.has_voice_profile(str(current_user.id))

    return {
        "has_voice_profile": has_profile
    }


@router.delete("/voice")
async def delete_voice_profile(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's voice profile.

    This removes:
    - Voice encoding files from disk
    - has_voice_profile flag in database
    - All cached TTS audio for this user

    Returns:
        Success message confirming deletion
    """
    try:
        user_id = str(current_user.id)

        # Delete voice profile files
        await tts_service.delete_voice_profile(user_id)

        # Clear TTS cache for this user
        try:
            cleared_count = await tts_cache_service.clear_user_cache(user_id)
            logger.info(f"Cleared {cleared_count} cached TTS entries for user {current_user.id}")
        except Exception as cache_err:
            logger.warning(f"Failed to clear TTS cache: {cache_err}")
            # Don't fail the deletion if cache clear fails

        # Update database flag
        user = db.query(User).filter(User.id == current_user.id).first()
        if user:
            user.has_voice_profile = False
            db.commit()

        logger.info(f"Voice profile deleted for user {current_user.id}")

        return {
            "success": True,
            "message": "Voice profile deleted successfully"
        }

    except Exception as e:
        logger.error(f"Voice deletion failed for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice deletion failed: {str(e)}"
        )


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to convert to speech"),
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Synthesize speech using the user's voice profile with Redis caching.

    This endpoint checks cache first for instant responses on repeated phrases.
    Cache hit = <50ms response time (vs 2-3s for synthesis).

    Args:
        text: Text to synthesize
        current_user: Authenticated user (injected)

    Returns:
        StreamingResponse with audio/wav content
    """
    try:
        # Check if user has voice profile
        if not tts_service.has_voice_profile(str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No voice profile found. Please upload a voice sample first."
            )

        user_id = str(current_user.id)

        # Try to get from cache first
        cached_audio = await tts_cache_service.get(user_id, text)
        if cached_audio:
            logger.info(f"Returning cached audio for user {current_user.id} (instant response)")
            return StreamingResponse(
                io.BytesIO(cached_audio),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=synthesized_speech.wav",
                    "X-Cache-Status": "HIT"  # Indicate cache hit
                }
            )

        # Cache miss - synthesize speech
        logger.info(f"Synthesizing speech for user {current_user.id} (cache miss)")
        wav_array = await tts_service.synthesize_speech(
            user_id=user_id,
            text=text
        )

        # Convert numpy array to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, wav_array, tts_service.SAMPLE_RATE, format='WAV')
        wav_buffer.seek(0)
        wav_bytes = wav_buffer.getvalue()

        # Store in cache for future requests (async, don't block response)
        try:
            await tts_cache_service.set(user_id, text, wav_bytes)
        except Exception as cache_err:
            logger.warning(f"Failed to cache TTS response: {cache_err}")
            # Don't fail the request if caching fails

        # Return synthesized audio
        return StreamingResponse(
            io.BytesIO(wav_bytes),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=synthesized_speech.wav",
                "X-Cache-Status": "MISS"  # Indicate cache miss
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@router.get("/original-recording")
async def get_original_recording(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get the user's original voice recording.

    Returns the original audio file that was uploaded/recorded
    for voice profile creation.

    Returns:
        StreamingResponse with audio/wav content
    """
    try:
        # Check if user has voice profile
        if not tts_service.has_voice_profile(str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No voice profile found."
            )

        # Get reference audio path
        ref_audio_path = tts_service.get_ref_audio_path(str(current_user.id))
        if not ref_audio_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original recording not found. This may be from an older voice profile."
            )

        # Read the audio file
        import aiofiles
        async with aiofiles.open(ref_audio_path, 'rb') as f:
            audio_data = await f.read()

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=original_recording.wav"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get original recording for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve original recording: {str(e)}"
        )


@router.get("/voice-info")
async def get_voice_info(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get information about the user's voice profile including cache stats.

    Returns:
        has_voice_profile: Boolean
        has_original_recording: Boolean
        reference_text: String (the transcript used for training)
        cache_stats: Cache statistics (entries, size)
    """
    try:
        user_id = str(current_user.id)

        has_profile = tts_service.has_voice_profile(user_id)
        has_recording = tts_service.get_ref_audio_path(user_id) is not None
        ref_text = tts_service.get_ref_text(user_id)

        # Get cache stats
        cache_stats = await tts_cache_service.get_cache_stats(user_id)

        return {
            "has_voice_profile": has_profile,
            "has_original_recording": has_recording,
            "reference_text": ref_text,
            "cache_stats": cache_stats
        }

    except Exception as e:
        logger.error(f"Failed to get voice info for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voice info: {str(e)}"
        )


@router.post("/synthesize-async")
async def synthesize_speech_async_endpoint(
    text: str = Form(..., description="Text to convert to speech"),
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Start async TTS synthesis job (non-blocking).

    Returns job ID immediately. Use /tts/job/{job_id} to poll for status.

    Args:
        text: Text to synthesize
        current_user: Authenticated user (injected)

    Returns:
        job_id: Celery task ID for polling
        status: "queued"
    """
    try:
        # Check if user has voice profile
        if not tts_service.has_voice_profile(str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No voice profile found. Please upload a voice sample first."
            )

        user_id = str(current_user.id)

        # Submit to Celery
        task = synthesize_speech_async.delay(user_id, text)

        logger.info(f"Queued async TTS job {task.id} for user {current_user.id}")

        return {
            "job_id": task.id,
            "status": "queued",
            "message": "TTS synthesis job queued. Poll /tts/job/{job_id} for status."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue TTS job for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue TTS job: {str(e)}"
        )


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get status of async TTS synthesis job.

    Args:
        job_id: Celery task ID
        current_user: Authenticated user (injected)

    Returns:
        status: "pending", "processing", "success", "error"
        progress: 0-100 (if processing)
        result: Audio data (base64) if success
        error: Error message if failed
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state == 'PENDING':
            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Job is queued, waiting to start"
            }

        elif task_result.state == 'PROCESSING':
            meta = task_result.info or {}
            return {
                "job_id": job_id,
                "status": "processing",
                "progress": meta.get('progress', 0),
                "message": meta.get('status', 'Processing...')
            }

        elif task_result.state == 'SUCCESS':
            result = task_result.result
            return {
                "job_id": job_id,
                "status": "success",
                "result": result,
                "message": "Synthesis completed"
            }

        elif task_result.state == 'FAILURE':
            return {
                "job_id": job_id,
                "status": "error",
                "error": str(task_result.info),
                "message": "Job failed"
            }

        else:
            return {
                "job_id": job_id,
                "status": task_result.state.lower(),
                "message": f"Job state: {task_result.state}"
            }

    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )
