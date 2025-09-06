"""
Bot model
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

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

    # Relationships
    user = relationship("User", back_populates="bots")
    meeting = relationship("Meeting", back_populates="bots")