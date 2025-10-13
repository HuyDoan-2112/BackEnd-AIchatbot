from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from app.schemas.chat_responses import ChatMessage as ResponseChatMessage


class InMemoryHistoryStore:
    """
    Simple in-memory store for chat histories and rolling summaries.
    Keyed by a conversation identifier (you can use request.user or a real conversation_id).

    Note: This is process-local and non-persistent. Replace with a DB-backed store for production.
    """

    def __init__(self) -> None:
        self._messages: Dict[str, List[ResponseChatMessage]] = {}
        self._summaries: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get_recent(self, conversation_id: str, limit: int = 20) -> List[ResponseChatMessage]:
        async with self._lock:
            msgs = self._messages.get(conversation_id, [])
            return list(msgs[-limit:])

    async def append(self, conversation_id: str, messages: List[ResponseChatMessage]) -> None:
        async with self._lock:
            if conversation_id not in self._messages:
                self._messages[conversation_id] = []
            self._messages[conversation_id].extend(messages)

    async def get_summary(self, conversation_id: str) -> Optional[str]:
        async with self._lock:
            return self._summaries.get(conversation_id)

    async def set_summary(self, conversation_id: str, summary: str) -> None:
        async with self._lock:
            self._summaries[conversation_id] = summary

