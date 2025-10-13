import pydantic
from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    # user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Commented out for now

    # user = relationship("User", back_populates="documents")  # Commented out for now
    
    # company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)  # Commented out for now
    # company = relationship("Company", back_populates="documents")  # Commented out for now
    # project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)  # Commented out for now
    # project = relationship("Project", back_populates="documents")  # Commented out for now

    def __repr__(self):
        return f"<Document(title={self.title})>"