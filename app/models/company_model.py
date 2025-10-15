from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class Company(Base):
    __tablename__ = 'companies'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    memberships = relationship("CompanyMembership", back_populates="company", cascade="all, delete-orphan", overlaps="companies,users")
    users = relationship("User", secondary="company_memberships", back_populates="companies", overlaps="memberships,company_memberships")
    projects = relationship("Project", back_populates="company", cascade="all, delete")
    documents = relationship("Document", back_populates="company", cascade="all, delete")
    conversations = relationship("Conversation", back_populates="company", cascade="all, delete")
    assistant_presets = relationship("AssistantPreset", back_populates="company", cascade="all, delete")
    
    def __repr__(self):
        return f"<Company(name={self.name}, description={self.description}, location={self.location})>"
