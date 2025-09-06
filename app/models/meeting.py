"""
Meeting model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    meeting_url = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    digital_twin_id = Column(Integer)
    status = Column(String, default="scheduled")
    auto_join = Column(Boolean, default=True)
    transcript = Column(Text)
    summary = Column(Text)
    action_items = Column(JSON)
    participants = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Legacy fields for backward compatibility
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    calendar_id = Column(String)
    calendar_event_id = Column(String)

    # Relationships
    user = relationship("User", back_populates="meetings")
    bots = relationship("Bot", back_populates="meeting")