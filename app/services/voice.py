"""
Voice service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import List, BinaryIO
import os
import uuid

from app.core.config import settings
from app.services.voice_processing import generate_speech


async def process_audio_upload(db: Session, audio_file: UploadFile, user_id: int):
    """Process uploaded audio file"""
    # Generate unique filename
    file_extension = audio_file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    
    # Save file
    upload_dir = os.path.join(settings.RECORDING_PATH, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as buffer:
        content = await audio_file.read()
        buffer.write(content)
    
    # Create database record
    db_sample = VoiceSample(
        filename=audio_file.filename,
        file_path=file_path,
        user_id=user_id,
        processed="pending"
    )
    db.add(db_sample)
    db.commit()
    db.refresh(db_sample)
    
    # Start processing
    #task = process_voice_sample.delay(file_path, None)  # No twin_id for general upload
    
    return {
        "sample_id": db_sample.id,
        "task_id": task.id,
        "status": "processing"
    }


async def generate_voice_response(db: Session, text: str, twin_id: int, user_id: int) -> BinaryIO:
    """Generate voice response using digital twin's voice model"""
    # Verify twin ownership
    from app.services.digital_twin import get_digital_twin
    db_twin = await get_digital_twin(db, twin_id, user_id)
    if not db_twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    
    if not db_twin.voice_trained:
        raise HTTPException(status_code=400, detail="Voice model not trained for this twin")
    
    # Generate unique output filename
    output_filename = f"{uuid.uuid4()}.wav"
    output_dir = os.path.join(settings.RECORDING_PATH, "generated")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    
    # Generate speech
    task = generate_speech.delay(text, twin_id, output_path)
    result = task.get()  # Wait for completion
    
    # Return audio file stream
    with open(output_path, "rb") as audio_file:
        return audio_file


