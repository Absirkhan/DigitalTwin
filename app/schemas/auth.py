"""
Authentication schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    google_id: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    profile_picture: Optional[str] = None
    google_id: Optional[str] = None

    class Config:
        from_attributes = True


class GoogleAuthURL(BaseModel):
    auth_url: str


class GoogleCallback(BaseModel):
    code: str
    state: Optional[str] = None