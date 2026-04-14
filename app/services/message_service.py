from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from typing import List
from app.models.message import Message
from app.models.chat import Chat
from app.services.llm_service import llm_service

class MessageService:
    async def get_messages(self, db: AsyncSession, chat_id: int) -> List[Message]:
        result = await db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        )
        return result.scalars().all()
    
    async def send_message(self, db: AsyncSession, chat_id: int, content: str):
        user_msg = Message(chat_id=chat_id, role="user", content=content)
        db.add(user_msg)
        await db.flush()
        
        assistant_content = await llm_service.generate(content)
        
        assistant_msg = Message(chat_id=chat_id, role="assistant", content=assistant_content)
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(user_msg)
        await db.refresh(assistant_msg)
        
        await db.execute(
            update(Chat).where(Chat.id == chat_id).values(updated_at=func.now())
        )
        await db.commit()
        
        return user_msg, assistant_msg

message_service = MessageService()
