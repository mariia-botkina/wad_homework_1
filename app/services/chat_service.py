from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from app.models.chat import Chat
from app.models.message import Message

class ChatService:
    async def create_chat(self, db: AsyncSession, user_id: int, title: str = "New Chat") -> Chat:
        chat = Chat(user_id=user_id, title=title)
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat
    
    async def get_chats(self, db: AsyncSession, user_id: int) -> List[Chat]:
        result = await db.execute(
            select(Chat).where(Chat.user_id == user_id).order_by(desc(Chat.updated_at))
        )
        return result.scalars().all()
    
    async def get_chat(self, db: AsyncSession, chat_id: int, user_id: int) -> Optional[Chat]:
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def delete_chat(self, db: AsyncSession, chat_id: int, user_id: int) -> bool:
        chat = await self.get_chat(db, chat_id, user_id)
        if not chat:
            return False
        await db.delete(chat)
        await db.commit()
        return True
    
    async def update_chat_title(self, db: AsyncSession, chat_id: int, user_id: int, title: str) -> Optional[Chat]:
        chat = await self.get_chat(db, chat_id, user_id)
        if not chat:
            return None
        chat.title = title
        await db.commit()
        await db.refresh(chat)
        return chat

chat_service = ChatService()
