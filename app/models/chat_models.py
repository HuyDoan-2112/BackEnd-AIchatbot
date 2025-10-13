from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Enum, func, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid
import enum
    
class Chat(Base):
    __tablename__ = 'chats'
    
    # ID chinh
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_archived = Column (Boolean, default=False, nullable=False)
    
    
    