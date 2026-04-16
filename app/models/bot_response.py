"""
Bot Response Model

Tracks all bot responses in meetings including what triggered the response,
what was said, and whether the injection was successful.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class BotResponse(Base):
    """
    Model for tracking bot responses in meetings.

    Stores each instance where the bot spoke in a meeting, including:
    - What triggered the response (speaker's message)
    - What the bot said in response
    - Response style used
    - Success status and latency metrics
    """
    __tablename__ = "bot_responses"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String, nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Content
    trigger_text = Column(Text, nullable=False)  # What the speaker said
    response_text = Column(Text, nullable=False)  # What bot replied
    response_style = Column(String(20), nullable=False)  # professional, casual, technical, brief

    # Audio
    audio_url = Column(Text, nullable=True)  # Optional: stored MP3 file path

    # Metadata
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    success = Column(Boolean, default=True, nullable=False)  # Was injection successful?
    latency_ms = Column(Integer, nullable=True)  # Total response generation time
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    meeting = relationship("Meeting", back_populates="bot_responses")

    def __repr__(self):
        return f"<BotResponse(id={self.id}, meeting_id={self.meeting_id}, success={self.success})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "meeting_id": self.meeting_id,
            "trigger_text": self.trigger_text,
            "response_text": self.response_text,
            "response_style": self.response_style,
            "audio_url": self.audio_url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
