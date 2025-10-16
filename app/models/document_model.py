from sqlalchemy import Column, ForeignKey, String, DateTime, Text, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete="CASCADE"), nullable=False, index=True)
    
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    file_type = Column(String, nullable=True)  # pdf, txt, docx, etc.
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)  # Extracted text content
    
    # Vector embedding for RAG search (stored as array of floats)
    vector_embedding = Column(ARRAY(Float), nullable=True)  # For semantic search
    
    # Metadata
    file_size_bytes = Column(Integer, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    citations = relationship("MessageCitation", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(filename={self.filename}, project_id={self.project_id})>"
