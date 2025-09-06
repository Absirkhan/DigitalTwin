"""
Email model
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String)
    subject = Column(String)
    sender = Column(String)
    snippet = Column(Text)

    # Relationships
    user = relationship("User", back_populates="emails")