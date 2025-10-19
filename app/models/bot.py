"""
Bot model
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    bot_id = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String)
    bot_name = Column(String)
    video_download_url = Column(String)
    transcript_url = Column(String)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="SET NULL"))
    
    # Recording-related fields
    recording_status = Column(String, default="pending")  # pending, recording, completed, failed
    recording_data = Column(JSON)  # Store full recording response from Recall API
    video_recording_url = Column(String)  # Direct download URL for video recording
    recording_expires_at = Column(DateTime)  # When the recording link expires
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="bots")
    meeting = relationship("Meeting", back_populates="bots")