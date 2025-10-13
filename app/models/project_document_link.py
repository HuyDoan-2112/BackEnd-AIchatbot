from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class ProjectDocumentLink(Base):
    __tablename__ = "project_document_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="document_links")
    document = relationship("Document", back_populates="project_links")

    __table_args__ = (
        UniqueConstraint("project_id", "document_id", name="uq_project_document_link"),
    )
