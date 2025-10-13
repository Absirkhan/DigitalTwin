"""
User schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool

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

    class Config:
        from_attributes = True