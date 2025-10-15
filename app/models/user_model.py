from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
import uuid
from app.models.base import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)  # Fixed: Use Boolean instead of pydantic.conint
    refresh_token = Column(String, nullable=True)
    refresh_token_expires_at = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    auth_sessions = relationship("AuthSession", back_populates="user")
    company_memberships = relationship("CompanyMembership", back_populates="user", cascade="all, delete-orphan", overlaps="companies,users")
    companies = relationship("Company", secondary="company_memberships", back_populates="users", overlaps="company_memberships,memberships")
    conversation_memberships = relationship("ConversationParticipant", back_populates="user", cascade="all, delete-orphan")
    authored_messages = relationship("Message", back_populates="author")
    assistant_presets = relationship("AssistantPreset", back_populates="creator")
    
    def verify_password(self, password: str) -> bool:
        """Verify a plain password against the hashed password"""
        return pwd_context.verify(password, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain password"""
        return pwd_context.hash(password)

    def __repr__(self):
        return f"<User(username={self.username}, email={self.email}, full_name={self.full_name})>"
