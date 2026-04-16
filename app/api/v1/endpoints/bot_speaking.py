"""
Bot Speaking API Endpoints

Provides API endpoints for managing bot speaking functionality:
- Get bot response history for meetings
- Emergency disable bot speaking during meetings
- Get/update global bot speaking settings
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func

from app.core.database import get_async_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.bot_response import BotResponse
from app.services.auth import get_current_user
from app.schemas.bot_speaking import (
    BotResponseHistoryResponse,
    BotResponseItem,
    BotSpeakingSettingsResponse,
    BotSpeakingSettingsUpdate,
    MeetingBotSpeakingUpdate,
    BotSpeakingStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/meeting/{meeting_id}/responses",
    response_model=BotResponseHistoryResponse,
    summary="Get bot response history for a meeting"
)
async def get_meeting_bot_responses(
    meeting_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of responses to return"),
    offset: int = Query(0, ge=0, description="Number of responses to skip"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get bot response history for a specific meeting.

    Returns:
    - List of bot responses (trigger, response text, style, success, latency)
    - Total count
    - Meeting details
    """
    # Verify meeting belongs to user
    result = await db.execute(
        select(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == current_user.id
            )
        )
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found or does not belong to you"
        )

    # Refresh meeting to ensure all attributes are loaded
    await db.refresh(meeting)

    # Get total count
    count_result = await db.execute(
        select(func.count(BotResponse.id)).filter(
            BotResponse.meeting_id == meeting_id
        )
    )
    total_responses = count_result.scalar() or 0

    # Get responses with pagination
    responses_result = await db.execute(
        select(BotResponse)
        .filter(BotResponse.meeting_id == meeting_id)
        .order_by(desc(BotResponse.timestamp))
        .offset(offset)
        .limit(limit)
    )
    responses = responses_result.scalars().all()

    # Convert to response items
    response_items = [
        BotResponseItem(
            id=resp.id,
            trigger_text=resp.trigger_text,
            response_text=resp.response_text,
            response_style=resp.response_style,
            timestamp=resp.timestamp,
            success=resp.success,
            latency_ms=resp.latency_ms,
            audio_url=resp.audio_url
        )
        for resp in responses
    ]

    logger.info(
        f"Retrieved {len(response_items)} bot responses for meeting {meeting_id}, "
        f"user_id={current_user.id}"
    )

    return BotResponseHistoryResponse(
        meeting_id=meeting_id,
        meeting_title=meeting.title,
        total_responses=total_responses,
        responses=response_items,
        bot_response_enabled=meeting.bot_response_enabled,
        bot_response_count=meeting.bot_response_count,
        bot_max_responses=meeting.bot_max_responses,
        bot_response_style=meeting.bot_response_style
    )


@router.post(
    "/meeting/{meeting_id}/disable",
    status_code=status.HTTP_200_OK,
    summary="Emergency disable bot speaking for a meeting"
)
async def emergency_disable_bot_speaking(
    meeting_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Emergency disable bot speaking for a specific meeting.

    Use this when:
    - Bot is responding inappropriately
    - Meeting is more important than expected
    - Need to stop bot from speaking immediately

    This ONLY disables for this specific meeting, not globally.
    """
    # Verify meeting belongs to user
    result = await db.execute(
        select(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == current_user.id
            )
        )
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found or does not belong to you"
        )

    # Disable bot speaking for this meeting
    was_enabled = meeting.bot_response_enabled
    meeting.bot_response_enabled = False

    await db.commit()

    logger.warning(
        f"[EMERGENCY DISABLE] Bot speaking disabled for meeting {meeting_id}, "
        f"user_id={current_user.id}, was_enabled={was_enabled}"
    )

    return {
        "success": True,
        "message": "Bot speaking disabled for this meeting",
        "meeting_id": meeting_id,
        "meeting_title": meeting.title,
        "was_enabled": was_enabled,
        "current_response_count": meeting.bot_response_count
    }


@router.patch(
    "/meeting/{meeting_id}/settings",
    status_code=status.HTTP_200_OK,
    summary="Update bot speaking settings for a meeting"
)
async def update_meeting_bot_speaking(
    meeting_id: int,
    settings: MeetingBotSpeakingUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update bot speaking settings for a specific meeting.

    Settings include:
    - bot_response_enabled: Enable/disable bot speaking
    - bot_response_style: Response style (professional, casual, technical, brief)
    - bot_max_responses: Maximum responses allowed
    """
    # Verify meeting belongs to user
    result = await db.execute(
        select(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == current_user.id
            )
        )
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found or does not belong to you"
        )

    # Update settings
    update_data = settings.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(meeting, field, value)

    await db.commit()
    await db.refresh(meeting)

    logger.info(
        f"Updated bot speaking settings for meeting {meeting_id}, "
        f"user_id={current_user.id}, changes={update_data}"
    )

    return {
        "success": True,
        "message": "Bot speaking settings updated",
        "meeting_id": meeting_id,
        "bot_response_enabled": meeting.bot_response_enabled,
        "bot_response_style": meeting.bot_response_style,
        "bot_max_responses": meeting.bot_max_responses
    }


@router.get(
    "/settings",
    response_model=BotSpeakingSettingsResponse,
    summary="Get global bot speaking settings"
)
async def get_bot_speaking_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get global bot speaking settings for the current user.

    Returns:
    - enable_bot_speaking: Global toggle for bot speaking feature
    - bot_name: Default name for the bot
    """
    # Refresh user to get latest data
    await db.refresh(current_user)

    return BotSpeakingSettingsResponse(
        enable_bot_speaking=current_user.enable_bot_speaking,
        bot_name=current_user.bot_name or "Assistant"
    )


@router.patch(
    "/settings",
    response_model=BotSpeakingSettingsResponse,
    summary="Update global bot speaking settings"
)
async def update_bot_speaking_settings(
    settings: BotSpeakingSettingsUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update global bot speaking settings for the current user.

    This is a global toggle - when disabled, bot will NOT speak in ANY meeting,
    regardless of per-meeting settings.
    """
    # Update settings
    update_data = settings.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    logger.info(
        f"Updated global bot speaking settings for user_id={current_user.id}, "
        f"changes={update_data}"
    )

    return BotSpeakingSettingsResponse(
        enable_bot_speaking=current_user.enable_bot_speaking,
        bot_name=current_user.bot_name or "Assistant"
    )


@router.get(
    "/stats",
    response_model=BotSpeakingStatsResponse,
    summary="Get bot speaking statistics"
)
async def get_bot_speaking_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get bot speaking statistics for the current user.

    Returns:
    - Total responses
    - Success rate
    - Average latency
    - Responses by style
    - Recent activity
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all responses for user's meetings in time period
    result = await db.execute(
        select(BotResponse)
        .join(Meeting, BotResponse.meeting_id == Meeting.id)
        .filter(
            and_(
                Meeting.user_id == current_user.id,
                BotResponse.timestamp >= cutoff_date
            )
        )
    )
    responses = result.scalars().all()

    if not responses:
        return BotSpeakingStatsResponse(
            total_responses=0,
            successful_responses=0,
            failed_responses=0,
            success_rate=0.0,
            average_latency_ms=0,
            responses_by_style={},
            total_meetings_with_responses=0,
            period_days=days
        )

    # Calculate statistics
    total_responses = len(responses)
    successful_responses = sum(1 for r in responses if r.success)
    failed_responses = total_responses - successful_responses
    success_rate = (successful_responses / total_responses * 100) if total_responses > 0 else 0.0

    # Average latency (only successful responses)
    latencies = [r.latency_ms for r in responses if r.success and r.latency_ms is not None]
    average_latency_ms = int(sum(latencies) / len(latencies)) if latencies else 0

    # Responses by style
    responses_by_style = {}
    for response in responses:
        style = response.response_style
        if style not in responses_by_style:
            responses_by_style[style] = 0
        responses_by_style[style] += 1

    # Count unique meetings
    unique_meetings = len(set(r.meeting_id for r in responses))

    logger.info(
        f"Retrieved bot speaking stats for user_id={current_user.id}, "
        f"period={days}d, total_responses={total_responses}"
    )

    return BotSpeakingStatsResponse(
        total_responses=total_responses,
        successful_responses=successful_responses,
        failed_responses=failed_responses,
        success_rate=round(success_rate, 2),
        average_latency_ms=average_latency_ms,
        responses_by_style=responses_by_style,
        total_meetings_with_responses=unique_meetings,
        period_days=days
    )
