"""
Models for assistant tool calls and results.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String, nullable=False)
    arguments_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="tool_calls")
    result = relationship("ToolResult", back_populates="tool_call", uselist=False, cascade="all, delete-orphan")


class ToolResult(Base):
    __tablename__ = "tool_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_call_id = Column(UUID(as_uuid=True), ForeignKey("tool_calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    result_json = Column(JSONB, nullable=True)
    error_text = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tool_call = relationship("ToolCall", back_populates="result")
