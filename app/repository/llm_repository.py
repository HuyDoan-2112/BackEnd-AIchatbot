from typing import List, Dict, Any, Optional

from app.schemas.chat_responses import ChatCompletionRequest, ChatCompletionResponse, ChatMessage as ResponseChatMessage, ChatRole
from app.services.history_store import InMemoryHistoryStore


class LLMRepository:

    def __init__(self, api_key: str = None, base_url: str = None, history_store: Optional[InMemoryHistoryStore] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.history_store = history_store or InMemoryHistoryStore()

    async def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # Placeholder for provider-specific calls if needed in future
        raise NotImplementedError("Provider chat_completion not implemented here; use ChatService")

    async def chat_completion_stream(self, model: str, messages: List[Dict[str, str]], **kwargs):
        # Placeholder for provider-specific streaming
        raise NotImplementedError("Provider streaming not implemented here; use ChatService")
        yield  # pragma: no cover

    async def count_tokens(self, text: str, model: str) -> int:
        # Optional, can be delegated to a tokenizer if needed
        return max(1, len(text) // 4)

    async def save_message_chain(self, request: ChatCompletionRequest, response: ChatCompletionResponse) -> None:
        """
        Save the latest user + assistant messages into the in-memory history store.
        Uses request.user as the conversation key if provided.
        """
        conv_id = None
        metadata = request.metadata or {}
        if isinstance(metadata, dict):
            conv_id = metadata.get("conversation_id") or metadata.get("session_id")
        if not conv_id and request.user:
            conv_id = request.user
        if not conv_id:
            conv_id = f"default:{request.model}"

        # Persist last user message (if present) and the assistant reply
        user_msg: Optional[ResponseChatMessage] = None
        for m in reversed(request.messages):
            if m.role == ChatRole.USER:
                user_msg = m
                break

        assistant_msg: Optional[ResponseChatMessage] = None
        if response.choices:
            assistant_msg = response.choices[0].message

        to_save: List[ResponseChatMessage] = []
        if user_msg is not None:
            to_save.append(user_msg)
        if assistant_msg is not None:
            to_save.append(assistant_msg)

        if to_save:
            await self.history_store.append(conv_id, to_save)


llm_repository = LLMRepository()
