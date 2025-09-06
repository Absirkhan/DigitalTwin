"""
Voice processing endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.auth import get_current_user
from app.services.voice import (
    process_audio_upload,
    generate_voice_response
)
from app.models.user import User

router = APIRouter()


@router.post("/upload")
async def upload_voice_sample(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload voice sample for training"""
    return await process_audio_upload(db, audio_file, current_user.id)


@router.post("/generate")
async def generate_voice(
    text: str,
    twin_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate voice response using digital twin's voice model"""
    audio_stream = await generate_voice_response(db, text, twin_id, current_user.id)
    return StreamingResponse(
        audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=response.wav"}
    )


@router.get("/samples/{twin_id}")
async def get_twin_voice_samples(
    twin_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get voice samples for a digital twin"""
    return await get_voice_samples(db, twin_id, current_user.id)