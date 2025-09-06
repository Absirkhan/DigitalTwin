"""
User service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional

from app.models.user import User
from app.schemas.user import UserUpdate


async def get_user_profile(db: Session, user_id: int) -> Optional[User]:
    """Get user profile"""
    return db.query(User).filter(User.id == user_id).first()


async def update_user_profile(db: Session, user_id: int, user_update: UserUpdate) -> User:
    """Update user profile"""
    db_user = await get_user_profile(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user