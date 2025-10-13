from __future__ import annotations

from typing import List, Optional, Sequence
from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from app.schemas.chat_responses import ChatMessage as ResponseChatMessage, ChatRole
from app.services.history_store import InMemoryHistoryStore
from app.services.retrieval_service import QdrantRetriever
from app.utils.tokenizer import Tokenizer


@dataclass
class BuildParams:
    max_prompt_tokens: int = 3000
    reserve_completion_tokens: int = 512
    sliding_window_turns: int = 12
    include_retrieval: bool = True
    keep_last_n_user_turns: int = 1


class ContextEngine:
    """
    Builds a well-structured context for chat completions:
    - Instruction hierarchy: system → session → retrieved context → summary → recent turns → latest user
    - Sliding window over recent turns
    - Optional retrieval from Qdrant
    - Token budgeting and pruning
    - Rolling summary support (externalized in HistoryStore)
    """

    def __init__(
        self,
        history: InMemoryHistoryStore,
        retriever: Optional[QdrantRetriever] = None,
        tokenizer: Optional[Tokenizer] = None,
        retrieval_top_k: int = 3,
    ) -> None:
        self.history = history
        self.retriever = retriever
        self.tokenizer = tokenizer or Tokenizer()
        self.retrieval_top_k = max(1, retrieval_top_k)

    def _to_lc(self, msg: ResponseChatMessage) -> Optional[BaseMessage]:
        role = msg.role.value if isinstance(msg.role, ChatRole) else msg.role
        content = msg.content or ""
        if role == ChatRole.SYSTEM.value:
            return SystemMessage(content=content)
        if role == ChatRole.USER.value:
            return HumanMessage(content=content)
        if role == ChatRole.ASSISTANT.value:
            return AIMessage(content=content)
        # Skip tool/function for now
        return None

    def _to_response_message(self, lc: BaseMessage) -> ResponseChatMessage:
        if lc.type == "system":
            return ResponseChatMessage(role=ChatRole.SYSTEM, content=str(lc.content))
        if lc.type == "human":
            return ResponseChatMessage(role=ChatRole.USER, content=str(lc.content))
        return ResponseChatMessage(role=ChatRole.ASSISTANT, content=str(lc.content))

    async def build(
        self,
        provided_messages: Sequence[ResponseChatMessage],
        *,
        conversation_id: Optional[str],
        base_system_prompt: str = "You are a helpful assistant.",
        session_constraints: Optional[str] = None,
        params: Optional[BuildParams] = None,
    ) -> List[BaseMessage]:
        p = params or BuildParams()

        # Determine if we need to fetch prior history. If caller provided few messages, augment with stored history
        provided = list(provided_messages)
        history_msgs: List[ResponseChatMessage] = []
        if conversation_id and len(provided) < 2:
            history_msgs = await self.history.get_recent(conversation_id, limit=p.sliding_window_turns * 2)

        # Build base stack: instructions
        stack: List[BaseMessage] = [SystemMessage(content=base_system_prompt)]
        if session_constraints:
            stack.append(SystemMessage(content=session_constraints))

        # Rolling summary
        if conversation_id:
            summary = await self.history.get_summary(conversation_id)
            if summary:
                stack.append(SystemMessage(content=f"Conversation summary (for context only):\n{summary}"))

        # Retrieval context from Qdrant
        if p.include_retrieval and self.retriever is not None:
            latest_user = None
            for m in reversed(provided):
                r = m.role.value if isinstance(m.role, ChatRole) else m.role
                if r == ChatRole.USER.value and (m.content or "").strip():
                    latest_user = m.content
                    break
            if latest_user:
                docs = await self.retriever.asearch(latest_user, k=self.retrieval_top_k)
                if docs:
                    joined = "\n\n".join(docs)
                    stack.append(SystemMessage(content=f"Relevant context (retrieved):\n---\n{joined}\n---\nUse only if relevant. If uncertain, say you are unsure."))

        # Recent turns via sliding window
        window_source = (history_msgs + provided) if history_msgs else provided
        # Keep only the last N turns
        if len(window_source) > p.sliding_window_turns * 2:
            window_source = window_source[-p.sliding_window_turns * 2 :]
        for m in window_source:
            lc = self._to_lc(m)
            if lc is not None:
                stack.append(lc)

        # Apply token budget pruning
        max_prompt_tokens = max(512, p.max_prompt_tokens - p.reserve_completion_tokens)
        stack = self.tokenizer.prune_to_budget(stack, max_prompt_tokens=max_prompt_tokens, keep_last_n_user_turns=p.keep_last_n_user_turns)

        return stack

    async def update_summary(
        self,
        chat_model,
        *,
        conversation_id: str,
        max_summary_tokens: int = 256,
    ) -> Optional[str]:
        """
        Update rolling summary using the last few turns and the prior summary.
        Uses the provided chat_model to generate a concise running summary.
        """
        if not conversation_id:
            return None

        recent = await self.history.get_recent(conversation_id, limit=16)
        prior = await self.history.get_summary(conversation_id)

        parts: List[BaseMessage] = [
            SystemMessage(
                content=(
                    "You are a summarizer. Update the conversation summary with the new turns.\n"
                    "Keep factual, concise (<= 120 words), and capture user goals and constraints."
                )
            )
        ]
        if prior:
            parts.append(SystemMessage(content=f"Previous summary:\n{prior}"))
        for m in recent:
            lc = self._to_lc(m)
            if lc is not None:
                parts.append(lc)

        # Budget for summary prompt
        parts = self.tokenizer.prune_to_budget(parts, max_prompt_tokens=max(256, max_summary_tokens))

        try:
            ai = await chat_model.ainvoke(parts)
            summary_text = getattr(ai, "content", None)
            if isinstance(summary_text, str) and summary_text.strip():
                await self.history.set_summary(conversation_id, summary_text.strip())
                return summary_text.strip()
        except Exception:
            return prior
        return prior
