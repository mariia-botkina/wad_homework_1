from pydantic import BaseModel
from datetime import datetime

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SendMessageRequest(BaseModel):
    content: str

class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
