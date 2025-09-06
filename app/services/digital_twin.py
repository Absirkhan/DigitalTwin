"""
Digital Twin service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import List, Optional
import os

from app.models.digital_twin import DigitalTwin
from app.schemas.digital_twin import DigitalTwinCreate, DigitalTwinUpdate
from app.services.voice_processing import process_voice_sample
from app.core.config import settings


async def create_digital_twin(db: Session, twin: DigitalTwinCreate, user_id: int) -> DigitalTwin:
    """Create a new digital twin"""
    db_twin = DigitalTwin(
        name=twin.name,
        description=twin.description,
        owner_id=user_id,
        personality_traits=twin.personality_traits,
        communication_style=twin.communication_style,
        response_patterns=twin.response_patterns,
        meeting_preferences=twin.meeting_preferences
    )
    db.add(db_twin)
    db.commit()
    db.refresh(db_twin)
    return db_twin


async def get_user_digital_twins(db: Session, user_id: int) -> List[DigitalTwin]:
    """Get all digital twins for a user"""
    return db.query(DigitalTwin).filter(
        DigitalTwin.owner_id == user_id,
        DigitalTwin.is_active == True
    ).all()


async def get_digital_twin(db: Session, twin_id: int, user_id: int) -> Optional[DigitalTwin]:
    """Get a specific digital twin"""
    return db.query(DigitalTwin).filter(
        DigitalTwin.id == twin_id,
        DigitalTwin.owner_id == user_id,
        DigitalTwin.is_active == True
    ).first()


async def update_digital_twin(db: Session, twin_id: int, twin_update: DigitalTwinUpdate, user_id: int) -> DigitalTwin:
    """Update a digital twin"""
    db_twin = await get_digital_twin(db, twin_id, user_id)
    if not db_twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    
    update_data = twin_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_twin, field, value)
    
    db.commit()
    db.refresh(db_twin)
    return db_twin


async def delete_digital_twin(db: Session, twin_id: int, user_id: int):
    """Delete a digital twin (soft delete)"""
    db_twin = await get_digital_twin(db, twin_id, user_id)
    if not db_twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    
    db_twin.is_active = False
    db.commit()


async def train_voice_model(db: Session, twin_id: int, audio_file: UploadFile, user_id: int):
    """Train voice model for digital twin"""
    # Verify twin ownership
    db_twin = await get_digital_twin(db, twin_id, user_id)
    if not db_twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    
    # Save audio file
    audio_dir = os.path.join(settings.RECORDING_PATH, f"twin_{twin_id}")
    os.makedirs(audio_dir, exist_ok=True)
    
    file_path = os.path.join(audio_dir, f"sample_{audio_file.filename}")
    with open(file_path, "wb") as buffer:
        content = await audio_file.read()
        buffer.write(content)
    
    # Start background processing
    task = process_voice_sample.delay(file_path, twin_id)
    
    return {
        "message": "Voice training started",
        "task_id": task.id,
        "status": "processing"
    }