from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class InteractionBase(BaseModel):
    hcp_name: str
    interaction_type: str = "Meeting"
    interaction_date: Optional[datetime] = None
    attendees: List[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: str = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    interaction_date: Optional[datetime] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionOut(InteractionBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hcp_id: str
    source: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[str] = []
    interaction: Optional[InteractionOut] = None
