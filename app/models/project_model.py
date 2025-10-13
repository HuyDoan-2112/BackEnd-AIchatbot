from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
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

    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime(timezone=True), nullable=True)

    chat_links = relationship("ProjectChatLink", back_populates="project", cascade="all, delete-orphan")
    company = relationship("Company", back_populates="projects")
    document_links = relationship("ProjectDocumentLink", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name={self.name}, description={self.description}, start_date={self.start_date}, end_date={self.end_date})>"
    
