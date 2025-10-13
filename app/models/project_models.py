import pydantic
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    # company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)  # Commented out for now
    # user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Commented out for now

    # company = relationship("Company", back_populates="projects")  # Commented out for now
    # user = relationship("User", back_populates="projects")  # Commented out for now
    # documents = relationship("Document", back_populates="project")  # Commented out for now

    def __repr__(self):
        return f"<Project(name={self.name}, description={self.description}, start_date={self.start_date}, end_date={self.end_date})>"
    
