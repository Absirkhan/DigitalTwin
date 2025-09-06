"""
User model
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(String)
    google_id = Column(String)
    credentials = Column(JSON)
    bot_name = Column(String)
    enable_backend_tasks = Column(Boolean)
    profile_picture = Column(String)

    # Relationships
    bots = relationship("Bot", back_populates="user")
    meetings = relationship("Meeting", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")
    emails = relationship("Email", back_populates="user")