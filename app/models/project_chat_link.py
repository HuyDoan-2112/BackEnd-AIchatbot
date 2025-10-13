from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.base import Base

class ProjectChatLink(Base):
    __tablename__ = "project_chat_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.conversation_id", ondelete="CASCADE"), nullable=False)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    project = relationship("Project", back_populates="chat_links")
    chat = relationship("Chat", back_populates="project_links")

    __table_args__ = (
        UniqueConstraint("project_id", "chat_id", name="uq_project_chat_link"),
    )
