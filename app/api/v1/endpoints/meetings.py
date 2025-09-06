"""
Meeting management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate, MeetingJoinRequest, MeetingJoinResponse
from app.services.auth import get_current_user
from app.services.meeting import (
    create_meeting,
    get_user_meetings,
    get_meeting,
    update_meeting,
    delete_meeting,
    join_meeting_with_twin
)
from app.services import recall_service
from app.models.user import User
from app.models.bot import Bot
from app.core.config import settings

router = APIRouter()


@router.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration"""
    return {
        "recall_api_key_configured": bool(settings.RECALL_API_KEY),
        "recall_api_key_length": len(settings.RECALL_API_KEY) if settings.RECALL_API_KEY else 0,
        "recall_base_url": settings.RECALL_BASE_URL,
        "recall_api_key_last_4": settings.RECALL_API_KEY[-4:] if settings.RECALL_API_KEY else "None"
    }


@router.post("/debug/test-auth")
async def test_recall_auth():
    """Test Recall API authentication"""
    return await recall_service.test_authentication()


@router.post("/", response_model=MeetingResponse)
async def create_meeting_schedule(
    meeting: MeetingCreate,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a meeting for digital twin attendance"""
    # return await create_meeting(db, meeting, current_user.id)
    return await create_meeting(db, meeting, 1)  # Using dummy user_id = 1


@router.get("/", response_model=List[MeetingResponse])
async def get_my_meetings(
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all meetings for current user"""
    # return await get_user_meetings(db, current_user.id)
    return await get_user_meetings(db, 1)  # Using dummy user_id = 1


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_details(
    meeting_id: int,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific meeting details"""
    # meeting = await get_meeting(db, meeting_id, current_user.id)
    meeting = await get_meeting(db, meeting_id, 1)  # Using dummy user_id = 1
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting_schedule(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update meeting schedule"""
    # return await update_meeting(db, meeting_id, meeting_update, current_user.id)
    return await update_meeting(db, meeting_id, meeting_update, 1)  # Using dummy user_id = 1


@router.delete("/{meeting_id}")
async def delete_meeting_schedule(
    meeting_id: int,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete meeting schedule"""
    # await delete_meeting(db, meeting_id, current_user.id)
    await delete_meeting(db, meeting_id, 1)  # Using dummy user_id = 1
    return {"message": "Meeting deleted successfully"}


@router.post("/{meeting_id}/join")
async def join_meeting(
    meeting_id: int,
    twin_id: int,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join meeting with digital twin"""
    # return await join_meeting_with_twin(db, meeting_id, twin_id, current_user.id)
    return await join_meeting_with_twin(db, meeting_id, twin_id, 1)  # Using dummy user_id = 1


@router.post("/join", response_model=MeetingJoinResponse)
async def join_meeting_with_url(
    request: MeetingJoinRequest,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """Join a meeting using the Recall API and save the bot to the database."""
    try:
        # Set default bot name if not provided
        if not request.bot_name:
            request.bot_name = "Digital Twin Bot"

        # 2. Join the meeting via Recall API
        response_data = await recall_service.join_meeting(request)

        # 3. Save the bot to the database if successful
        if response_data.success and response_data.bot_id:
            existing_bot = db.query(Bot).filter(Bot.bot_id == response_data.bot_id).first()
            if not existing_bot:
                # Use the bot name from request
                bot_name = request.bot_name
                new_bot = Bot(
                    bot_id=response_data.bot_id,
                    user_id=1,  # Using dummy user_id = 1
                    bot_name=bot_name,
                    # platform and meeting_id can be populated later via webhooks or status checks
                )
                db.add(new_bot)
                db.commit()

        return response_data

    except Exception as e:
        db.rollback()
        logging.error(f"Error in join_meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")