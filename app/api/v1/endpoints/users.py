"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth import get_current_user_bearer
from app.services.user import get_user_profile, update_user_profile
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user_bearer)):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    return await update_user_profile(db, current_user.id, user_update)