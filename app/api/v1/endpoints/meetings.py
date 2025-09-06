"""
Meeting management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate
from app.services.auth import get_current_user
from app.services.meeting import (
    create_meeting,
    get_user_meetings,
    get_meeting,
    update_meeting,
    delete_meeting,
    join_meeting_with_twin
)
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=MeetingResponse)
async def create_meeting_schedule(
    meeting: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a meeting for digital twin attendance"""
    return await create_meeting(db, meeting, current_user.id)


@router.get("/", response_model=List[MeetingResponse])
async def get_my_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all meetings for current user"""
    return await get_user_meetings(db, current_user.id)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_details(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific meeting details"""
    meeting = await get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting_schedule(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update meeting schedule"""
    return await update_meeting(db, meeting_id, meeting_update, current_user.id)


@router.delete("/{meeting_id}")
async def delete_meeting_schedule(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete meeting schedule"""
    await delete_meeting(db, meeting_id, current_user.id)
    return {"message": "Meeting deleted successfully"}


@router.post("/{meeting_id}/join")
async def join_meeting(
    meeting_id: int,
    twin_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join meeting with digital twin"""
    return await join_meeting_with_twin(db, meeting_id, twin_id, current_user.id)