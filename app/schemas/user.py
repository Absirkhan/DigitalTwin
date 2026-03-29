"""
User schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bot_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    bot_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    has_voice_profile: bool = False

    class Config:
        from_attributes = True


class DigitalTwinProfileUpdate(BaseModel):
    """Schema for updating digital twin profile settings"""
    bot_name: Optional[str] = None
    profile_picture: Optional[str] = None  # URL or base64 string


class DigitalTwinProfileResponse(BaseModel):
    """Schema for digital twin profile response"""
    user_id: int
    bot_name: Optional[str] = None
    profile_picture: Optional[str] = None
    full_name: Optional[str] = None
    email: str
    has_voice_profile: bool = False

    class Config:
        from_attributes = True