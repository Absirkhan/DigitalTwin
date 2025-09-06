"""
Meeting service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime

from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.services.meeting_automation import schedule_meeting_join


async def create_meeting(db: Session, meeting: MeetingCreate, user_id: int) -> Meeting:
    """Create a new meeting"""
    db_meeting = Meeting(
        title=meeting.title,
        description=meeting.description,
        meeting_url=meeting.meeting_url,
        platform=meeting.platform,
        scheduled_time=meeting.scheduled_time,
        duration_minutes=meeting.duration_minutes or 60,
        user_id=user_id,
        digital_twin_id=meeting.digital_twin_id,
        auto_join=meeting.auto_join,
        status="scheduled"
    )
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    
    # Schedule automatic joining if enabled
    if db_meeting.auto_join and db_meeting.digital_twin_id:
        try:
            from app.services.meeting_automation import schedule_meeting_join
            schedule_meeting_join.delay(
                db_meeting.id,
                db_meeting.digital_twin_id,
                db_meeting.meeting_url,
                db_meeting.platform,
                db_meeting.scheduled_time
            )
        except Exception as e:
            # Log error but don't fail meeting creation
            print(f"Failed to schedule meeting join: {e}")
    
    return db_meeting


async def get_user_meetings(db: Session, user_id: int) -> List[Meeting]:
    """Get all meetings for a user"""
    return db.query(Meeting).filter(Meeting.user_id == user_id).all()


async def get_meeting(db: Session, meeting_id: int, user_id: int) -> Optional[Meeting]:
    """Get a specific meeting"""
    return db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user_id
    ).first()


async def update_meeting(db: Session, meeting_id: int, meeting_update: MeetingUpdate, user_id: int) -> Meeting:
    """Update a meeting"""
    db_meeting = await get_meeting(db, meeting_id, user_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    update_data = meeting_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_meeting, field, value)
    
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


async def delete_meeting(db: Session, meeting_id: int, user_id: int):
    """Delete a meeting"""
    db_meeting = await get_meeting(db, meeting_id, user_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    db.delete(db_meeting)
    db.commit()


async def join_meeting_with_twin(db: Session, meeting_id: int, twin_id: int, user_id: int):
    """Join meeting with digital twin"""
    db_meeting = await get_meeting(db, meeting_id, user_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Update meeting with twin assignment
    db_meeting.digital_twin_id = twin_id
    db_meeting.status = "in_progress"
    db.commit()
    
    # Start meeting automation
    from app.services.meeting_automation import join_meeting_task
    task = join_meeting_task.delay(
        meeting_id,
        twin_id,
        db_meeting.meeting_url,
        db_meeting.platform
    )
    
    return {
        "message": "Digital twin is joining the meeting",
        "task_id": task.id,
        "status": "joining"
    }