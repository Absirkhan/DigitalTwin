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

    class Config:
        from_attributes = True