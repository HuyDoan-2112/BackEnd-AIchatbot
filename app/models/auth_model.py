from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class AuthSession(Base):
    """Authentication session model"""
    __tablename__ = "auth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="auth_sessions")
    
    def __repr__(self):
        return f"<AuthSession(user_id={self.user_id}, expires_at={self.expires_at}, revoked={self.revoked})>"
