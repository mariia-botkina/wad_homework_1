from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.chat_service import chat_service
from app.services.message_service import message_service
from app.schemas.message import MessageResponse, SendMessageRequest, SendMessageResponse

router = APIRouter(prefix="/api/chats", tags=["messages"])

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(chat_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = await chat_service.get_chat(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await message_service.get_messages(db, chat_id)

@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await chat_service.get_chat(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    user_msg, assistant_msg = await message_service.send_message(db, chat_id, body.content)
    return SendMessageResponse(user_message=user_msg, assistant_message=assistant_msg)
