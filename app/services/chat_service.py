from typing import AsyncGenerator, Optional
from uuid import uuid4

from app.schemas.chat_responses import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatCompletionChoice,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    Usage,
    ChatMessage as ResponseChatMessage,
    ChatRole,
)
from langchain.chat_models import init_chat_model
from app.core.model_registry import get_model_registry
import asyncio
import logging
import time
from app.core.config import get_settings
from app.services.history_store import InMemoryHistoryStore
from app.services.context_engine import ContextEngine, BuildParams
from app.services.retrieval_service import build_default_retriever
from app.repository.llm_repository import llm_repository as default_llm_repo
from app.utils.tokenizer import Tokenizer

logger = logging.getLogger(__name__)
class ChatService:

    # """Handles logic for chat completion requests."""
    def __init__(self, llm_repository=None):
        self.llm_repository = llm_repository or default_llm_repo
        self.settings = get_settings()
        self.history_store = getattr(self.llm_repository, "history_store", InMemoryHistoryStore())
        self.tokenizer = Tokenizer(self.settings.MODEL_NAME)
        self.context_engine = ContextEngine(
            history=self.history_store,
            retriever=build_default_retriever(),
            tokenizer=self.tokenizer,
            retrieval_top_k=self.settings.RETRIEVAL_TOP_K,
        )

    def _resolve_conversation_id(self, request: ChatCompletionRequest) -> str:
        metadata = request.metadata or {}
        conversation_id = None
        if isinstance(metadata, dict):
            conversation_id = metadata.get("conversation_id") or metadata.get("session_id")
        if conversation_id:
            return str(conversation_id)
        if request.user:
            return request.user
        return f"default:{request.model}"

    async def create_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        # Get the model from the registry
        start_time = time.time()
        request_id = str(uuid4())
        logger.info(f"[{request_id}] Chat request received for model: {request.model}")
        
        registry = get_model_registry()
        chat_model_config = registry.get_chat_model(request.model)
        if not chat_model_config:
            raise ValueError(f"Model '{request.model}' not found in registry")

        chat_model = init_chat_model(**chat_model_config)

        # Determine conversation key (user field or metadata override)
        conversation_id = self._resolve_conversation_id(request)

        # Build structured context
        base_system_prompt = "You are a helpful assistant."
        provided_messages = list(request.messages)
        if provided_messages and provided_messages[0].role == ChatRole.SYSTEM:
            base_system_prompt = provided_messages[0].content or base_system_prompt
            provided_messages = provided_messages[1:]

        session_constraints: Optional[str] = None
        if isinstance(request.metadata, dict):
            session_constraints = request.metadata.get("session_constraints")

        final_messages = await self.context_engine.build(
            provided_messages=provided_messages,
            conversation_id=conversation_id,
            base_system_prompt=base_system_prompt,
            session_constraints=session_constraints,
            params=BuildParams(
                max_prompt_tokens=self.settings.MODEL_CONTEXT_WINDOW,
                reserve_completion_tokens=self.settings.MODEL_COMPLETION_RESERVE,
                sliding_window_turns=12,
                include_retrieval=self.context_engine.retriever is not None,
                keep_last_n_user_turns=1,
            ),
        )

        # Call the LLM using the built context
        try:
            ai_obj = await chat_model.ainvoke(final_messages)
        except Exception as e:
            logger.exception("Error invoking model")
            raise e
        
        # Persist messages and update summary
        try:
            # Get last user message from request (after trimming system prompt)
            last_user = None
            for m in reversed(provided_messages):
                if m.role == ChatRole.USER and (m.content or "").strip():
                    last_user = m
                    break
            assistant_msg = ResponseChatMessage(role=ChatRole.ASSISTANT, content=getattr(ai_obj, "content", str(ai_obj)))
            to_save = []
            if last_user is not None:
                to_save.append(last_user)
            to_save.append(assistant_msg)
            await self.history_store.append(conversation_id, to_save)
            # Update rolling summary asynchronously (do not block response)
            asyncio.create_task(self.context_engine.update_summary(chat_model, conversation_id=conversation_id))
        except Exception:
            logger.debug("History persistence or summary update failed; continuing")

        # Usage estimation (rough)
        prompt_tokens = self.tokenizer.count_messages(final_messages)
        completion_tokens = self.tokenizer.count_text(getattr(ai_obj, "content", ""))
        usage = Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=prompt_tokens + completion_tokens)
        # Build response schema
        response = ChatCompletionResponse(
            id=request_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=assistant_msg,
                    finish_reason="stop"
                )
            ],
            usage=usage
        )

        logger.info(f"[{request_id}] Completed in {time.time() - start_time:.2f}s")
        return response
        # return response
    
    async def create_completion_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[ChatCompletionChunk, None]:
        # Processes chat completion with streaming (token-by-toke or chunk-by-chunk)
        request_id = str(uuid4())
        registry = get_model_registry()
        chat_model_config = registry.get_chat_model(request.model)
        chat_model = init_chat_model(**chat_model_config)

        # Build context for streaming as well
        conversation_id = self._resolve_conversation_id(request)
        base_system_prompt = "You are a helpful assistant."
        provided_messages = list(request.messages)
        if provided_messages and provided_messages[0].role == ChatRole.SYSTEM:
            base_system_prompt = provided_messages[0].content or base_system_prompt
            provided_messages = provided_messages[1:]
        final_messages = await self.context_engine.build(
            provided_messages=provided_messages,
            conversation_id=conversation_id,
            base_system_prompt=base_system_prompt,
            session_constraints=None,
        )
        # Use the model for streaming
        try:
            # Simulate streaming chunks from LLM
            async for token in chat_model.astream(final_messages):
                chunk = ChatCompletionChunk(
                    id=request_id,
                    created=int(time.time()),
                    model=request.model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=ChatCompletionChunkDelta(
                                role="assistant",
                                content=token
                            ),
                            finish_reason=None
                        )
                    ]
                )
                yield chunk
                await asyncio.sleep(0.01) # simulate delay
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            raise e
    
    async def count_tokens(self, text: str, model: str) -> int:
        """
        Returns the number of tokens for given text under a model.
        Useful for usage tracking.
        """
        try:
            tokenizer = Tokenizer(model)
            return tokenizer.count_text(text)
        except Exception as e:
            logger.warning(f"Token count failed for model {model}: {str(e)}")
            return len(text.split())

    async def create_new_conversation(self, user: Optional[str] = None) -> str:
        """
        Creates a new conversation ID.
        If user is provided, the conversation ID is prefixed with the user ID.
        """
        if user:
            return f"{user}:{uuid4()}"
        return str(uuid4())

chat_service = ChatService()
