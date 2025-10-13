import pydantic
from typing import Optional
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    
    # users = relationship("User", back_populates="company")  # Commented out for now
    # projects = relationship("Project", back_populates="company")  # Commented out for now
    # documents = relationship("Document", back_populates="company")  # Commented out for now
    
    def __repr__(self):
        return f"<Company(name={self.name}, description={self.description}, location={self.location})>"