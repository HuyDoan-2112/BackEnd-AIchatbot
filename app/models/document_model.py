from sqlalchemy import Column, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete="CASCADE"), nullable=True)
    
    company = relationship("Company", back_populates="documents")
    project_links = relationship("ProjectDocument", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("MessageCitation", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(title={self.title})>"
