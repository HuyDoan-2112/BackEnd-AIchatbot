from app.db.postgresql import get_db_connection
from app.core.response_status import *
from app.models.chat_model import Chat
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class ChatRepository:
    
    def __init__(self):
        self.db_connection = None
    
    def _get_db_connection(self):
        """Get database connection instance"""
        if self.db_connection is None:
            self.db_connection = get_db_connection()
        return self.db_connection

    async def create_chat(self, model: str, name: Optional[str], created_by: Optional[str]) -> Dict[str, Any]:
        """Create a new chat conversation in the database"""
        try:
            async for session in self._get_db_connection().get_session():
                new_chat = Chat(model=model, name=name, created_by=created_by, conversation_id=uuid.uuid4(), is_archived=False, updated_at=datetime.now())
                session.add(new_chat)
                await session.commit()
                await session.refresh(new_chat)
                return (
                    OK(message="Chat created successfully", data={
                        "conversation_id": new_chat.conversation_id,
                        "model": new_chat.model,
                        "name": new_chat.name,
                        "created_by": new_chat.created_by,
                        "created_at": new_chat.created_at,
                        "is_archived": new_chat.is_archived,
                        "updated_at": new_chat.updated_at,
                    })
                )
        except Exception as e:
            return InternalError(message=f"Failed to create chat: {str(e)}", error_code="5000")
    
    async def get_chat_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(Chat).filter(Chat.conversation_id == conversation_id))
                chat = result.scalar_one_or_none()
                return {
                    "conversation_id": chat.conversation_id,
                    "model": chat.model,
                    "name": chat.name,
                    "created_by": chat.created_by,
                    "created_at": chat.created_at,
                } if chat else ChatNotFound(message="Chat not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to get chat by ID: {str(e)}", error_code="5000")
        
    async def update_chat(self, conversation_id: str, name: Optional[str], is_archived: Optional[bool]) -> Dict[str, Any]:
        """Update chat details"""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(Chat).filter(Chat.conversation_id == conversation_id))
                chat = result.scalar_one_or_none()
                if not chat:
                    return ChatNotFound(message="Chat not found", error_code="4004")
                
                if name is not None:
                    chat.name = name
                if is_archived is not None:
                    chat.is_archived = is_archived
                chat.updated_at = datetime.now()
                
                session.add(chat)
                await session.commit()
                await session.refresh(chat)
                
                return OK(message="Chat updated successfully", data={
                    "conversation_id": chat.conversation_id,
                    "model": chat.model,
                    "name": chat.name,
                    "created_by": chat.created_by,
                    "created_at": chat.created_at,
                    "is_archived": chat.is_archived,
                    "updated_at": chat.updated_at,
                })
        except Exception as e:
            return InternalError(message=f"Failed to update chat: {str(e)}", error_code="5000")
        
    async def delete_chat(self, conversation_id: str) -> Dict[str, Any]:
        """Delete a chat conversation from the database"""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(Chat).filter(Chat.conversation_id == conversation_id))
                chat = result.scalar_one_or_none()
                if not chat:
                    return ChatNotFound(message="Chat not found", error_code="4004")
                
                await session.execute(update(Chat).where(Chat.conversation_id == conversation_id).values(is_archived=True, updated_at=datetime.now()))
                await session.commit()
                
                return OK(message="Chat deleted successfully", data={
                    "conversation_id": conversation_id,
                    "deleted": True
                })
        except Exception as e:
            return InternalError(message=f"Failed to delete chat: {str(e)}", error_code="5000")

    async def get_conversations_by_conversation_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(Chat).filter(Chat.conversation_id == conversation_id))
                chat = result.scalar_one_or_none()
                return {
                    "conversation_id": chat.conversation_id,
                    "model": chat.model,
                    "name": chat.name,
                    "created_by": chat.created_by,
                    "created_at": chat.created_at,
                } if chat else ChatNotFound(message="Chat not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to get chat by ID: {str(e)}", error_code="5000")
