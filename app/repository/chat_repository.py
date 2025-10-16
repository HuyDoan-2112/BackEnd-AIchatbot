from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from app.core.response_status import *
from app.db.postgresql import get_db_connection
from app.models.conversation_model import Conversation, ConversationParticipant
from app.models.message_model import (
    Message,
    MessageAttachment,
    MessageCitation,
    MessageRevision,
    MessageStreamChunk,
    MessageUsage,
)


class ChatRepository:
    """
    Repository responsible for working with conversation data (formerly chats).
    """

    def __init__(self):
        self.db_connection = None

    def _get_db_connection(self):
        """Get database connection instance"""
        if self.db_connection is None:
            self.db_connection = get_db_connection()
        return self.db_connection

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_conversation(conversation: Conversation) -> Dict[str, Any]:
        return {
            "conversation_id": str(conversation.conversation_id),
            "title": conversation.title,
            "model": conversation.model,
            "created_by": str(conversation.created_by) if conversation.created_by else None,
            "project_id": str(conversation.project_id) if conversation.project_id else None,
            "preset_id": str(conversation.preset_id) if conversation.preset_id else None,
            "is_archived": conversation.is_archived,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------
    async def user_has_access(self, conversation_id: str, user_id: str) -> bool:
        """Check if a user has access to a conversation (creator or participant)."""
        try:
            async for session in self._get_db_connection().get_session():
                # Check creator
                result = await session.execute(
                    select(Conversation).where(
                        Conversation.conversation_id == conversation_id,
                        Conversation.created_by == user_id,
                    )
                )
                if result.scalar_one_or_none() is not None:
                    return True

                # Check participant
                result = await session.execute(
                    select(ConversationParticipant).where(
                        ConversationParticipant.conversation_id == conversation_id,
                        ConversationParticipant.user_id == user_id,
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            return False

    async def create_chat(
        self,
        company_id: Optional[str],
        project_id: Optional[str],
        title: Optional[str],
        created_by: Optional[str],
        model: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new chat conversation in the database.

        Note: company_id is accepted for forward compatibility but is not yet stored
        on the Conversation model.
        """
        if not project_id:
            return ValidationError(message="project_id is required to create a chat", error_code="4002")

        try:
            async for session in self._get_db_connection().get_session():
                new_chat = Conversation(
                    project_id=project_id,
                    title=title,
                    model_label=model,
                    created_by=created_by,
                    preset_id=preset_id,
                    is_archived=False,
                )
                session.add(new_chat)
                await session.commit()
                await session.refresh(new_chat)
                return OK(
                    message="Chat created successfully",
                    data=self._serialize_conversation(new_chat),
                )
        except Exception as e:
            return InternalError(message=f"Failed to create chat: {str(e)}", error_code="5000")

    async def get_chat_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a conversation by identifier."""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(
                    select(Conversation).filter(Conversation.conversation_id == conversation_id)
                )
                chat = result.scalar_one_or_none()
                return (
                    self._serialize_conversation(chat)
                    if chat
                    else ChatNotFound(message="Chat not found", error_code="4004")
                )
        except Exception as e:
            return InternalError(message=f"Failed to get chat by ID: {str(e)}", error_code="5000")

    async def list_chats(
        self,
        *,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List conversations filtered by project or company, newest first."""
        try:
            async for session in self._get_db_connection().get_session():
                order_expr = func.coalesce(Conversation.updated_at, Conversation.created_at)
                stmt = select(Conversation).order_by(order_expr.desc()).limit(limit)
                if project_id:
                    stmt = stmt.where(Conversation.project_id == project_id)
                if company_id:
                    stmt = stmt.where(Conversation.company_id == company_id)

                result = await session.execute(stmt)
                chats = result.scalars().all()
                return [self._serialize_conversation(chat) for chat in chats]
        except Exception as e:
            return InternalError(message=f"Failed to list chats: {str(e)}", error_code="5000")

    async def list_chats_for_user(
        self,
        user_id: str,
        *,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List conversations visible to a user (creator or participant), newest first."""
        try:
            async for session in self._get_db_connection().get_session():
                order_expr = func.coalesce(Conversation.updated_at, Conversation.created_at)

                # Base query: conversations created by user OR where user participates
                stmt = (
                    select(Conversation)
                    .outerjoin(
                        ConversationParticipant,
                        (ConversationParticipant.conversation_id == Conversation.conversation_id)
                        & (ConversationParticipant.user_id == user_id),
                    )
                    .where(
                        (Conversation.created_by == user_id)
                        | (ConversationParticipant.user_id == user_id)
                    )
                    .order_by(order_expr.desc())
                    .limit(limit)
                )

                if project_id:
                    stmt = stmt.where(Conversation.project_id == project_id)
                if company_id:
                    stmt = stmt.where(Conversation.company_id == company_id)

                result = await session.execute(stmt)
                chats = result.scalars().unique().all()
                return [self._serialize_conversation(chat) for chat in chats]
        except Exception as e:
            return InternalError(message=f"Failed to list user chats: {str(e)}", error_code="5000")

    async def update_chat(
        self,
        conversation_id: str,
        *,
        title: Optional[str] = None,
        model: Optional[str] = None,
        preset_id: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update conversation metadata."""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(
                    select(Conversation).filter(Conversation.conversation_id == conversation_id)
                )
                chat = result.scalar_one_or_none()
                if not chat:
                    return ChatNotFound(message="Chat not found", error_code="4004")

                if title is not None:
                    chat.title = title
                if model is not None:
                    chat.model_label = model
                if preset_id is not None:
                    chat.preset_id = preset_id
                if is_archived is not None:
                    chat.is_archived = is_archived

                chat.updated_at = datetime.now(tz=timezone.utc)

                session.add(chat)
                await session.commit()
                await session.refresh(chat)

                return OK(
                    message="Chat updated successfully",
                    data=self._serialize_conversation(chat),
                )
        except Exception as e:
            return InternalError(message=f"Failed to update chat: {str(e)}", error_code="5000")

    async def delete_chat(self, conversation_id: str) -> Dict[str, Any]:
        """Soft-delete a conversation by marking it archived."""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(
                    select(Conversation).filter(Conversation.conversation_id == conversation_id)
                )
                chat = result.scalar_one_or_none()
                if not chat:
                    return ChatNotFound(message="Chat not found", error_code="4004")

                await session.execute(
                    update(Conversation)
                    .where(Conversation.conversation_id == conversation_id)
                    .values(
                        is_archived=True,
                        updated_at=datetime.now(tz=timezone.utc),
                    )
                )
                await session.commit()

                return OK(
                    message="Chat archived successfully",
                    data={"conversation_id": conversation_id, "deleted": True},
                )
        except Exception as e:
            return InternalError(message=f"Failed to delete chat: {str(e)}", error_code="5000")

    # ------------------------------------------------------------------
    # Participant management
    # ------------------------------------------------------------------
    async def add_participant(
        self,
        conversation_id: str,
        user_id: str,
        role: str = "member",
    ) -> Dict[str, Any]:
        """Ensure a participant entry exists for the conversation."""
        try:
            async for session in self._get_db_connection().get_session():
                # Check existing
                existing = await session.get(
                    ConversationParticipant,
                    (conversation_id, user_id),
                )
                if existing:
                    existing.role = role
                    session.add(existing)
                else:
                    participant = ConversationParticipant(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        role=role,
                    )
                    session.add(participant)
                await session.commit()
                return OK(message="Participant added")
        except Exception as e:
            return InternalError(message=f"Failed to add participant: {str(e)}", error_code="5000")

    async def remove_participant(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """Remove a participant from the conversation."""
        try:
            async for session in self._get_db_connection().get_session():
                participant = await session.get(
                    ConversationParticipant,
                    (conversation_id, user_id),
                )
                if not participant:
                    return NotFound(message="Participant not found", error_code="4004")
                await session.delete(participant)
                await session.commit()
                return OK(message="Participant removed")
        except Exception as e:
            return InternalError(message=f"Failed to remove participant: {str(e)}", error_code="5000")

    async def list_participants(self, conversation_id: str) -> List[Dict[str, Any]]:
        """List all participants for a conversation."""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(
                    select(ConversationParticipant).where(
                        ConversationParticipant.conversation_id == conversation_id
                    )
                )
                participants = result.scalars().all()
                return [
                    {
                        "conversation_id": str(p.conversation_id),
                        "user_id": str(p.user_id),
                        "role": p.role,
                        "added_at": p.added_at,
                    }
                    for p in participants
                ]
        except Exception as e:
            return InternalError(message=f"Failed to list participants: {str(e)}", error_code="5000")

    # ------------------------------------------------------------------
    # Message helpers (lightweight for now)
    # ------------------------------------------------------------------
    async def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        author_user_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        state: str = "final",
        model_label: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Message:
        try:
            async for session in self._get_db_connection().get_session():
                message = Message(
                    conversation_id=conversation_id,
                    parent_message_id=parent_message_id,
                    author_user_id=author_user_id,
                    role=role,
                    content=content,
                    state=state,
                    model_label=model_label,
                    temperature=temperature,
                    top_p=top_p,
                )
                session.add(message)
                await session.commit()
                await session.refresh(message)
                return message
        except Exception as e:
            return InternalError(message=f"Failed to create message: {str(e)}", error_code="5000")

    async def list_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
        include_children: bool = False,
        include_artifacts: bool = False,
        include_usage: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Return recent messages for a conversation.
        By default fetches latest N messages on the main branch (parentless chain).
        """
        try:
            async for session in self._get_db_connection().get_session():
                stmt = (
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.desc())
                    .limit(limit)
                )
                if include_children:
                    stmt = stmt.options(selectinload(Message.children))
                if include_artifacts:
                    stmt = stmt.options(
                        selectinload(Message.attachments),
                        selectinload(Message.citations),
                        selectinload(Message.stream_chunks),
                    )
                if include_usage:
                    stmt = stmt.options(selectinload(Message.usage))
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [
                    self._serialize_message(
                        msg,
                        include_children=include_children,
                        include_artifacts=include_artifacts,
                        include_usage=include_usage,
                    )
                    for msg in messages
                ]
        except Exception as e:
            return InternalError(message=f"Failed to list messages: {str(e)}", error_code="5000")

    async def add_message_revision(
        self,
        message_id: str,
        content: str,
        *,
        model_label: Optional[str] = None,
        rev_no: Optional[int] = None,
    ) -> MessageRevision:
        try:
            async for session in self._get_db_connection().get_session():
                next_rev = rev_no
                if next_rev is None:
                    result = await session.execute(
                        select(func.max(MessageRevision.rev_no)).where(MessageRevision.message_id == message_id)
                    )
                    current_max = result.scalar()
                    next_rev = 1 if current_max is None else current_max + 1

                revision = MessageRevision(
                    message_id=message_id,
                    rev_no=next_rev,
                    content=content,
                    model_label=model_label,
                )
                session.add(revision)
                await session.commit()
                await session.refresh(revision)
                return revision
        except Exception as e:
            return InternalError(message=f"Failed to add message revision: {str(e)}", error_code="5000")

    async def append_stream_chunk(self, message_id: str, seq: int, delta: str) -> MessageStreamChunk:
        try:
            async for session in self._get_db_connection().get_session():
                chunk = MessageStreamChunk(message_id=message_id, seq=seq, delta=delta)
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)
                return chunk
        except Exception as e:
            return InternalError(message=f"Failed to append stream chunk: {str(e)}", error_code="5000")

    async def add_attachment(
        self,
        message_id: str,
        *,
        file_uri: str,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
    ) -> MessageAttachment:
        try:
            async for session in self._get_db_connection().get_session():
                attachment = MessageAttachment(
                    message_id=message_id,
                    file_uri=file_uri,
                    file_name=file_name,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                )
                session.add(attachment)
                await session.commit()
                await session.refresh(attachment)
                return attachment
        except Exception as e:
            return InternalError(message=f"Failed to add attachment: {str(e)}", error_code="5000")

    async def add_citation(
        self,
        message_id: str,
        document_id: str,
        *,
        score: Optional[float] = None,
        rationale: Optional[str] = None,
    ) -> MessageCitation:
        try:
            async for session in self._get_db_connection().get_session():
                citation = await session.get(MessageCitation, (message_id, document_id))
                if citation:
                    citation.score = score
                    citation.rationale = rationale
                else:
                    citation = MessageCitation(
                        message_id=message_id,
                        document_id=document_id,
                        score=score,
                        rationale=rationale,
                    )
                    session.add(citation)
                await session.commit()
                await session.refresh(citation)
                return citation
        except Exception as e:
            return InternalError(message=f"Failed to add citation: {str(e)}", error_code="5000")

    async def save_message_usage(
        self,
        message_id: str,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
    ) -> MessageUsage:
        try:
            async for session in self._get_db_connection().get_session():
                usage = await session.get(MessageUsage, message_id)
                total = prompt_tokens + completion_tokens
                if usage:
                    usage.prompt_tokens = prompt_tokens
                    usage.completion_tokens = completion_tokens
                    usage.total_tokens = total
                    usage.latency_ms = latency_ms
                    usage.cost_usd = cost_usd
                    session.add(usage)
                    target = usage
                else:
                    target = MessageUsage(
                        message_id=message_id,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total,
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                    )
                    session.add(target)
                await session.commit()
                await session.refresh(target)
                return target
        except Exception as e:
            return InternalError(message=f"Failed to save message usage: {str(e)}", error_code="5000")

    @staticmethod
    def _serialize_message(
        msg: Message,
        *,
        include_children: bool = False,
        include_artifacts: bool = False,
        include_usage: bool = False,
    ) -> Dict[str, Any]:
        payload = {
            "message_id": str(msg.id),
            "conversation_id": str(msg.conversation_id),
            "parent_message_id": str(msg.parent_message_id) if msg.parent_message_id else None,
            "author_user_id": str(msg.author_user_id) if msg.author_user_id else None,
            "role": msg.role,
            "content": msg.content,
            "state": msg.state,
            "model_label": msg.model_label,
            "temperature": msg.temperature,
            "top_p": msg.top_p,
            "created_at": msg.created_at,
        }
        if include_children:
            payload["children"] = [
                ChatRepository._serialize_message(child, include_children=False, include_artifacts=include_artifacts, include_usage=include_usage)
                for child in msg.children
            ]
        if include_artifacts:
            payload["attachments"] = [
                {
                    "id": str(attachment.id),
                    "file_uri": attachment.file_uri,
                    "file_name": attachment.file_name,
                    "mime_type": attachment.mime_type,
                    "size_bytes": attachment.size_bytes,
                    "created_at": attachment.created_at,
                }
                for attachment in getattr(msg, "attachments", [])
            ]
            payload["citations"] = [
                {
                    "document_id": str(citation.document_id),
                    "score": citation.score,
                    "rationale": citation.rationale,
                }
                for citation in getattr(msg, "citations", [])
            ]
            payload["tool_calls"] = [
                {
                    "id": str(call.id),
                    "tool_name": call.tool_name,
                    "arguments": call.arguments_json,
                    "result": call.result.result_json if call.result else None,
                    "error": call.result.error_text if call.result else None,
                    "created_at": call.created_at,
                }
                for call in getattr(msg, "tool_calls", [])
            ]
            payload["stream_chunks"] = [
                {
                    "seq": chunk.seq,
                    "delta": chunk.delta,
                }
                for chunk in getattr(msg, "stream_chunks", [])
            ]
        if include_usage and getattr(msg, "usage", None):
            payload["usage"] = {
                "prompt_tokens": msg.usage.prompt_tokens,
                "completion_tokens": msg.usage.completion_tokens,
                "total_tokens": msg.usage.total_tokens,
                "latency_ms": msg.usage.latency_ms,
                "cost_usd": msg.usage.cost_usd,
            }
        return payload
