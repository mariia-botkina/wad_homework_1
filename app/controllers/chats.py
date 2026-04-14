from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.chat_service import chat_service
from app.schemas.chat import ChatCreate, ChatResponse, ChatWithMessages

router = APIRouter(prefix="/api/chats", tags=["chats"])

@router.get("", response_model=List[ChatResponse])
async def list_chats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await chat_service.get_chats(db, current_user.id)

@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(body: ChatCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await chat_service.create_chat(db, current_user.id, body.title or "New Chat")

@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat(chat_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = await chat_service.get_chat(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    success = await chat_service.delete_chat(db, chat_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")

@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(chat_id: int, body: ChatCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = await chat_service.update_chat_title(db, chat_id, current_user.id, body.title or "New Chat")
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
