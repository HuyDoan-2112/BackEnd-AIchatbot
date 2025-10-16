"""
Organization model: Hierarchical structure for country/company/department.
Supports nested organizations with shared RAG stores.
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, default="company")  # country/company/department
    description = Column(String, nullable=True)
    
    # Hierarchical structure: self-referencing for parent organizations
    parent_organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # RAG configuration for this organization level
    rag_vector_store_id = Column(String, nullable=True)
    rag_config = Column(JSON, nullable=True)  # Store RAG settings as JSON
    
    # Metadata
    country = Column(String, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship(
        "Organization",
        remote_side="Organization.id",
        back_populates="children"
    )
    children = relationship(
        "Organization",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    memberships = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    assistant_presets = relationship(
        "AssistantPreset",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization(name={self.name}, type={self.type}, parent_id={self.parent_organization_id})>"
