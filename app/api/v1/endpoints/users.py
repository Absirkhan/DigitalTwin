"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db, SessionLocal
from app.schemas.user import UserResponse, UserUpdate, DigitalTwinProfileUpdate, DigitalTwinProfileResponse
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


# Digital Twin Profile Management Endpoints

@router.get("/digital-twin/profile", response_model=DigitalTwinProfileResponse)
async def get_digital_twin_profile(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get digital twin profile settings"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return DigitalTwinProfileResponse(
            user_id=user.id,
            bot_name=user.bot_name,
            profile_picture=user.profile_picture,
            full_name=user.full_name,
            email=user.email
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting digital twin profile: {str(e)}")


@router.put("/digital-twin/profile", response_model=DigitalTwinProfileResponse)
async def update_digital_twin_profile(
    profile_update: DigitalTwinProfileUpdate,
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Update digital twin profile settings (name and profile picture)"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update bot name if provided
        if profile_update.bot_name is not None:
            user.bot_name = profile_update.bot_name
        
        # Update profile picture if provided
        if profile_update.profile_picture is not None:
            user.profile_picture = profile_update.profile_picture
        
        db.commit()
        db.refresh(user)
        
        return DigitalTwinProfileResponse(
            user_id=user.id,
            bot_name=user.bot_name,
            profile_picture=user.profile_picture,
            full_name=user.full_name,
            email=user.email
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating digital twin profile: {str(e)}")


@router.get("/digital-twin/preview")
async def preview_digital_twin(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """Get a preview of how the digital twin will appear in meetings"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Show how the bot will appear
        display_name = user.bot_name or "Digital Twin Bot"
        
        return {
            "success": True,
            "preview": {
                "display_name": display_name,
                "profile_picture": user.profile_picture,
                "will_appear_as": f"Meeting participant: {display_name}",
                "settings": {
                    "custom_name": user.bot_name is not None,
                    "custom_picture": user.profile_picture is not None,
                    "fallback_name": "Digital Twin Bot" if not user.bot_name else None
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")