from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
import uuid
from app.models.base import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)  # Changed to String for UUID
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)  # Fixed: Use Boolean instead of pydantic.conint
    refresh_token = Column(String, nullable=True)
    refresh_token_expires_at = Column(Integer, nullable=True)
    created_at = Column(String, nullable=True)  # Store as string for now
    # company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)  # Commented out for now

    # company = relationship("Company", back_populates="users")  # Commented out for now
    auth_sessions = relationship("AuthSession", back_populates="user")
    
    def verify_password(self, password: str) -> bool:
        """Verify a plain password against the hashed password"""
        return pwd_context.verify(password, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain password"""
        return pwd_context.hash(password)

    def __repr__(self):
        return f"<User(username={self.username}, email={self.email}, full_name={self.full_name})>"