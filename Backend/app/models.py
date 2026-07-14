import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class HCP(Base):
    """A Healthcare Professional the field rep interacts with."""
    __tablename__ = "hcps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=True)
    hospital = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    """A single logged HCP interaction (meeting, call, email, etc.)."""
    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    hcp_id = Column(String(36), ForeignKey("hcps.id"), nullable=False)

    interaction_type = Column(Enum("Meeting", "Call", "Email", "Conference", name="interaction_type"),
                               default="Meeting")
    interaction_date = Column(DateTime, default=datetime.utcnow)

    attendees = Column(JSON, default=list)  # list[str]
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(JSON, default=list)  # list[str]
    samples_distributed = Column(JSON, default=list)  # list[str]

    sentiment = Column(Enum("Positive", "Neutral", "Negative", name="sentiment_type"), default="Neutral")
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)

    source = Column(Enum("form", "chat", name="source_type"), default="form")
    raw_chat_text = Column(Text, nullable=True)  # original free-text if logged via chat

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
