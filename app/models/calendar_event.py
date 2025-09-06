"""
Calendar Event model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String)
    summary = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    meeting_url = Column(String)
    participants = Column(JSON)

    # Relationships
    user = relationship("User", back_populates="calendar_events")