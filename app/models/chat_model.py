from sqlalchemy import Column, ForeignKey, String, Boolean, func, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid
    
class Chat(Base):
    __tablename__ = 'chats'
    
    # ID chinh
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_archived = Column (Boolean, default=False, nullable=False)
    
    
    company = relationship("Company", back_populates="chats")
    project_links = relationship("ProjectChatLink", back_populates="chat", cascade="all, delete-orphan")
    
    
