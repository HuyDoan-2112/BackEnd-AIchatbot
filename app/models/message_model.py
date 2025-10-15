"""
Message-centric models for conversations, supporting branching, revisions, citations, and usage.
"""
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    Float,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    state = Column(String, nullable=False, default="final")
    model_label = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    parent = relationship("Message", remote_side="Message.id", back_populates="children")
    children = relationship("Message", back_populates="parent", cascade="all, delete-orphan")
    author = relationship("User", back_populates="authored_messages")

    revisions = relationship("MessageRevision", back_populates="message", cascade="all, delete-orphan")
    stream_chunks = relationship("MessageStreamChunk", back_populates="message", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")
    citations = relationship("MessageCitation", back_populates="message", cascade="all, delete-orphan")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")
    usage = relationship("MessageUsage", back_populates="message", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system','tool')",
            name="ck_message_role",
        ),
        CheckConstraint(
            "state IN ('draft','streaming','final','error')",
            name="ck_message_state",
        ),
    )


class MessageStreamChunk(Base):
    __tablename__ = "message_stream_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    seq = Column(Integer, nullable=False)
    delta = Column(Text, nullable=False)

    message = relationship("Message", back_populates="stream_chunks")

    __table_args__ = (
        UniqueConstraint("message_id", "seq", name="uq_message_stream_chunk"),
    )


class MessageRevision(Base):
    __tablename__ = "message_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    rev_no = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    model_label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("message_id", "rev_no", name="uq_message_revision"),
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_uri = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="attachments")


class MessageCitation(Base):
    __tablename__ = "message_citations"

    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    score = Column(Float, nullable=True)
    rationale = Column(Text, nullable=True)

    message = relationship("Message", back_populates="citations")
    document = relationship("Document", back_populates="citations")


class MessageUsage(Base):
    __tablename__ = "message_usage"

    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    message = relationship("Message", back_populates="usage")
