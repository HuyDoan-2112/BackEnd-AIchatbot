from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Integer, Float, Boolean
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
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # RAG Configuration (embedded in project)
    rag_enabled = Column(Boolean, default=True)
    rag_vector_store_id = Column(String, nullable=True)
    rag_chunk_size = Column(Integer, default=1000)
    rag_chunk_overlap = Column(Integer, default=200)
    rag_config = Column(JSON, nullable=True)  # Additional RAG settings
    
    # Project Rules and Settings
    rules = Column(JSON, nullable=True)  # Department-specific rules/guidelines
    default_model = Column(String, default="gpt-4")  # Default AI model
    system_prompt = Column(String, nullable=True)  # Project-level instructions

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    assistant_presets = relationship("AssistantPreset", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name={self.name}, organization_id={self.organization_id})>"
    
