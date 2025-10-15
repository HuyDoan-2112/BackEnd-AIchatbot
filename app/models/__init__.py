"""
SQLAlchemy models package.
Import all models here to ensure relationships are properly resolved.
"""
from app.models.base import Base
from app.models.user_model import User
from app.models.company_model import Company
from app.models.auth_model import AuthSession
from app.models.project_model import Project
from app.models.document_model import Document
from app.models.project_conversation import ProjectConversation
from app.models.project_document import ProjectDocument
from app.models.company_membership_model import CompanyMembership
from app.models.conversation_model import Conversation, ConversationParticipant
from app.models.message_model import (
    Message,
    MessageStreamChunk,
    MessageRevision,
    MessageAttachment,
    MessageCitation,
    MessageUsage,
)
from app.models.tool_call_model import ToolCall, ToolResult
from app.models.assistant_preset_model import AssistantPreset

__all__ = [
    "Base",
    "User",
    "Company",
    "AuthSession",
    "Project",
    "Document",
    "ProjectConversation",
    "ProjectDocument",
    "CompanyMembership",
    "Conversation",
    "ConversationParticipant",
    "Message",
    "MessageStreamChunk",
    "MessageRevision",
    "MessageAttachment",
    "MessageCitation",
    "MessageUsage",
    "ToolCall",
    "ToolResult",
    "AssistantPreset",
]
