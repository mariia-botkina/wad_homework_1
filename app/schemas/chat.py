from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse] = []

from app.schemas.message import MessageResponse
ChatWithMessages.model_rebuild()
