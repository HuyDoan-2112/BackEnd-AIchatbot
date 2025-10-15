"""
Company membership model to associate users with companies.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class CompanyMembership(Base):
    __tablename__ = "company_memberships"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=False, default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="memberships", overlaps="companies,users")
    user = relationship("User", back_populates="company_memberships", overlaps="companies,users")
