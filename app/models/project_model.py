from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)

    conversation_links = relationship("ProjectConversation", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    company = relationship("Company", back_populates="projects")
    document_links = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    assistant_presets = relationship("AssistantPreset", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name={self.name}, description={self.description}, start_date={self.start_date}, end_date={self.end_date})>"
    
