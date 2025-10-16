"""
Assistant preset model for saved chat configurations.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class AssistantPreset(Base):
    __tablename__ = "assistant_presets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    system_prompt = Column(String, nullable=True)
    model_label = Column(String, nullable=False)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    tools_json = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="assistant_presets")
    project = relationship("Project", back_populates="assistant_presets")
    creator = relationship("User", back_populates="assistant_presets")
    conversations = relationship("Conversation", back_populates="preset")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_preset_name"),
    )
