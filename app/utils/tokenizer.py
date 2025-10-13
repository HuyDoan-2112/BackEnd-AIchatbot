from __future__ import annotations

from typing import List, Optional

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None  # graceful fallback

from langchain_core.messages import BaseMessage


class Tokenizer:
    """
    Token counting helper with optional tiktoken support.
    Falls back to a rough heuristic when tiktoken is unavailable.
    """

    def __init__(self, model_name: str = "gpt-3.5-turbo") -> None:
        self.model_name = model_name
        self._enc = None
        if tiktoken is not None:
            try:
                self._enc = tiktoken.encoding_for_model(model_name)
            except Exception:
                # Fallback to a common base encoding
                try:
                    self._enc = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self._enc = None

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        if self._enc is not None:
            try:
                return len(self._enc.encode(text))
            except Exception:
                pass
        # Heuristic: ~4 chars per token
        return max(1, len(text) // 4)

    def count_messages(self, messages: List[BaseMessage]) -> int:
        total = 0
        for m in messages:
            # Only count content; role tokens are negligible for rough budgeting here
            content = getattr(m, "content", None)
            if isinstance(content, str):
                total += self.count_text(content)
            elif isinstance(content, list):
                # Some message types can be list of parts; concat string parts
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict)]
                total += self.count_text("\n".join(text_parts))
        return total

    def prune_to_budget(
        self,
        messages: List[BaseMessage],
        max_prompt_tokens: int,
        keep_last_n_user_turns: int = 1,
    ) -> List[BaseMessage]:
        """
        Prune messages to fit within max_prompt_tokens using a simple strategy:
        1) keep the last `keep_last_n_user_turns` user turns and all following messages
        2) drop older assistant messages first
        3) drop older pairs until under budget
        """
        if self.count_messages(messages) <= max_prompt_tokens:
            return messages

        # Identify user turn boundaries
        user_indices = [i for i, m in enumerate(messages) if m.type == "human"]
        if user_indices:
            last_kept_user_idx = user_indices[-keep_last_n_user_turns] if len(user_indices) >= keep_last_n_user_turns else user_indices[0]
            # keep from last_kept_user_idx to end
            kept_tail = messages[last_kept_user_idx:]
        else:
            kept_tail = messages[-4:]  # rough fallback

        # Now include earlier context starting from the end, preferring user messages
        head = messages[: len(messages) - len(kept_tail)]

        # First drop older assistant messages
        pruned_head: List[BaseMessage] = []
        for m in head:
            if m.type == "ai":
                continue
            pruned_head.append(m)

        combined = pruned_head + kept_tail
        while self.count_messages(combined) > max_prompt_tokens and pruned_head:
            # Drop from the start until fits
            pruned_head = pruned_head[1:]
            combined = pruned_head + kept_tail

        # Final fallback: if still too big, keep only the kept_tail
        if self.count_messages(combined) > max_prompt_tokens:
            combined = kept_tail

        return combined

