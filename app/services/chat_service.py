from typing import AsyncGenerator, Optional, Dict, Any, List
from uuid import uuid4
import logging
import time

import httpx
from openai import AsyncOpenAI

from app.schemas.chat_response import (
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
from app.core.model_registry import get_model_registry
from app.core.config import get_settings
from app.services.history_store import InMemoryHistoryStore
from app.services.context_engine import ContextEngine, BuildParams
from app.services.retrieval_service import build_default_retriever
from app.services.cache_service import get_cache_service
from app.repository.llm_repository import llm_repository as default_llm_repo
from app.utils.tokenizer import Tokenizer

logger = logging.getLogger(__name__)
class ChatService:
    """Handles logic for chat completion requests using LM Studio (OpenAI-compatible API)."""

    def __init__(self, llm_repository=None):
        self.llm_repository = llm_repository or default_llm_repo
        self.settings = get_settings()
        self.history_store = getattr(self.llm_repository, "history_store", InMemoryHistoryStore())
        self.tokenizer = Tokenizer(self.settings.MODEL_NAME)
        self.cache_service = get_cache_service()
        self.context_engine = ContextEngine(
            history=self.history_store,
            retriever=build_default_retriever(),
            tokenizer=self.tokenizer,
            retrieval_top_k=self.settings.RETRIEVAL_TOP_K,
        )

        # Initialize HTTP client with HTTP/2 support and connection pooling
        http_client = httpx.AsyncClient(
            http2=True,  # Enable HTTP/2 for better performance
            limits=httpx.Limits(
                max_connections=100,  # Total connection pool size
                max_keepalive_connections=20,  # Persistent connections
                keepalive_expiry=30.0  # Keep connections alive for 30s
            ),
            timeout=httpx.Timeout(
                60.0,  # Default timeout
                connect=5.0  # Connection timeout
            )
        )

        # Initialize OpenAI client for LM Studio with optimized HTTP client
        self.client = AsyncOpenAI(
            base_url=self.settings.MODEL_BASE_URL or "http://localhost:1234/v1",
            api_key=self.settings.OPENAI_API_KEY or "lm-studio",  # LM Studio doesn't validate API key
            http_client=http_client
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

    def _convert_messages_to_openai_format(self, messages) -> List[Dict[str, Any]]:
        """Convert internal message format or LangChain BaseMessage to OpenAI API format."""
        from langchain_core.messages import BaseMessage

        openai_messages = []
        for msg in messages:
            # Handle LangChain BaseMessage objects
            if isinstance(msg, BaseMessage):
                # Map LangChain message types to OpenAI roles
                if msg.type == "system":
                    role = "system"
                elif msg.type == "human":
                    role = "user"
                elif msg.type == "ai":
                    role = "assistant"
                elif msg.type == "function":
                    role = "function"
                elif msg.type == "tool":
                    role = "tool"
                else:
                    role = "user"  # Default fallback

                message_dict = {
                    "role": role,
                    "content": str(msg.content) if msg.content else ""
                }

                # Handle additional attributes if present
                if hasattr(msg, 'name') and msg.name:
                    message_dict["name"] = msg.name
                if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                    message_dict["tool_call_id"] = msg.tool_call_id
                if hasattr(msg, 'additional_kwargs'):
                    if 'function_call' in msg.additional_kwargs:
                        message_dict["function_call"] = msg.additional_kwargs['function_call']
                    if 'tool_calls' in msg.additional_kwargs:
                        message_dict["tool_calls"] = msg.additional_kwargs['tool_calls']
            else:
                # Handle ResponseChatMessage objects (Pydantic models)
                message_dict = {"role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role)}
                if msg.content:
                    message_dict["content"] = msg.content
                if hasattr(msg, 'name') and msg.name:
                    message_dict["name"] = msg.name
                if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                    message_dict["tool_call_id"] = msg.tool_call_id
                if hasattr(msg, 'function_call') and msg.function_call:
                    message_dict["function_call"] = msg.function_call
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    message_dict["tool_calls"] = msg.tool_calls

            openai_messages.append(message_dict)
        return openai_messages

    async def create_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Create a non-streaming chat completion using LM Studio."""
        start_time = time.time()
        request_id = str(uuid4())

        # Performance tracking
        timings = {
            "cache_check": 0.0,
            "context_build": 0.0,
            "llm_call": 0.0,
            "history_save": 0.0,
            "total": 0.0
        }

        logger.info(f"[{request_id}] Chat request received for model: {request.model}")

        # Check cache first (for non-streaming requests with low temperature)
        cache_start = time.time()
        cache_key = None
        if self.settings.ENABLE_RESPONSE_CACHE and request.temperature and request.temperature < 0.3:
            openai_messages = self._convert_messages_to_openai_format(request.messages)
            cache_key = self.cache_service.generate_chat_cache_key(
                model=request.model,
                messages=openai_messages,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens
            )
            cached_response = await self.cache_service.get_chat_response(cache_key)
            timings["cache_check"] = time.time() - cache_start
            if cached_response:
                timings["total"] = time.time() - start_time
                logger.info(f"[{request_id}] Cache HIT - {timings['total']:.3f}s")
                # Convert cached dict back to response model
                try:
                    return ChatCompletionResponse(**cached_response)
                except Exception as e:
                    logger.warning(f"[{request_id}] Failed to parse cached response: {e}")
        else:
            timings["cache_check"] = time.time() - cache_start

        # Validate model exists in registry
        registry = get_model_registry()
        chat_model_config = registry.get_chat_model(request.model)
        if not chat_model_config:
            raise ValueError(f"Model '{request.model}' not found in registry")

        # Determine conversation key
        conversation_id = self._resolve_conversation_id(request)

        # Build structured context with history and retrieval
        base_system_prompt = "You are a helpful assistant."
        provided_messages = list(request.messages)
        if provided_messages and provided_messages[0].role == ChatRole.SYSTEM:
            base_system_prompt = provided_messages[0].content or base_system_prompt
            provided_messages = provided_messages[1:]

        session_constraints: Optional[str] = None
        if isinstance(request.metadata, dict):
            session_constraints = request.metadata.get("session_constraints")

        context_start = time.time()
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
        timings["context_build"] = time.time() - context_start

        # Convert to OpenAI format and call LM Studio
        openai_messages = self._convert_messages_to_openai_format(final_messages)

        try:
            # Call LM Studio using OpenAI client
            llm_start = time.time()
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=openai_messages,
                temperature=request.temperature or self.settings.MODEL_TEMPERATURE,
                max_tokens=request.max_tokens or self.settings.MODEL_MAX_OUTPUT_TOKENS,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=False
            )
            timings["llm_call"] = time.time() - llm_start

            # Extract the completion
            assistant_content = response.choices[0].message.content or ""
            assistant_msg = ResponseChatMessage(role=ChatRole.ASSISTANT, content=assistant_content)

        except Exception as e:
            logger.exception(f"[{request_id}] Error calling LM Studio API")
            raise ValueError(f"LM Studio API error: {str(e)}")

        # Persist messages and update summary
        history_start = time.time()
        try:
            # Get last user message from request (after trimming system prompt)
            last_user = None
            for m in reversed(provided_messages):
                if m.role == ChatRole.USER and (m.content or "").strip():
                    last_user = m
                    break

            to_save = []
            if last_user is not None:
                to_save.append(last_user)
            to_save.append(assistant_msg)
            await self.history_store.append(conversation_id, to_save)

            # Update rolling summary asynchronously (do not block response)
            # Note: We can't pass LangChain model here anymore, need to refactor summary if needed
            # asyncio.create_task(self.context_engine.update_summary(chat_model, conversation_id=conversation_id))
        except Exception as ex:
            logger.debug(f"History persistence failed: {ex}")
        timings["history_save"] = time.time() - history_start

        # Get actual usage from LM Studio response or estimate
        if hasattr(response, 'usage') and response.usage:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        else:
            # Fallback to estimation
            prompt_tokens = self.tokenizer.count_messages(final_messages)
            completion_tokens = self.tokenizer.count_text(assistant_content)
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )

        # Build OpenAI-compatible response
        chat_response = ChatCompletionResponse(
            id=response.id if hasattr(response, 'id') else request_id,
            created=response.created if hasattr(response, 'created') else int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=assistant_msg,
                    finish_reason=response.choices[0].finish_reason or "stop"
                )
            ],
            usage=usage
        )

        # Cache the response if caching is enabled and cache_key was generated
        if cache_key and self.settings.ENABLE_RESPONSE_CACHE:
            try:
                await self.cache_service.set_chat_response(
                    cache_key,
                    chat_response.model_dump(),
                    ttl=self.settings.REDIS_CACHE_TTL
                )
                logger.debug(f"[{request_id}] Response cached with key: {cache_key}")
            except Exception as e:
                logger.warning(f"[{request_id}] Failed to cache response: {e}")

        timings["total"] = time.time() - start_time
        logger.info(
            f"[{request_id}] Completed - Total: {timings['total']:.3f}s | "
            f"Cache: {timings['cache_check']:.3f}s | Context: {timings['context_build']:.3f}s | "
            f"LLM: {timings['llm_call']:.3f}s | History: {timings['history_save']:.3f}s"
        )
        return chat_response
    
    def _send_status_chunk(
        self,
        request_id: str,
        model: str,
        status_message: str
    ) -> ChatCompletionChunk:
        """Create a status/thinking chunk to show progress."""
        return ChatCompletionChunk(
            id=request_id,
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(
                        role=ChatRole.ASSISTANT,
                        thinking=status_message  # Use thinking field instead of content
                    ),
                    finish_reason=None
                )
            ]
        )

    async def create_completion_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Create a streaming chat completion with real-time progress updates."""
        request_id = str(uuid4())
        logger.info(f"[{request_id}] Streaming chat request for model: {request.model}")

        # Send initial "thinking" status (if enabled)
        if self.settings.STREAM_SHOW_THINKING:
            yield self._send_status_chunk(request_id, request.model, "Processing your request...")

        # Validate model exists in registry
        try:
            registry = get_model_registry()
            chat_model_config = registry.get_chat_model(request.model)
            if not chat_model_config:
                raise ValueError(f"Model '{request.model}' not found in registry")
        except Exception as e:
            logger.error(f"[{request_id}] Model validation failed: {e}")
            raise

        # Build context for streaming with progress updates
        conversation_id = self._resolve_conversation_id(request)
        base_system_prompt = "You are a helpful assistant."
        provided_messages = list(request.messages)
        if provided_messages and provided_messages[0].role == ChatRole.SYSTEM:
            base_system_prompt = provided_messages[0].content or base_system_prompt
            provided_messages = provided_messages[1:]

        session_constraints: Optional[str] = None
        if isinstance(request.metadata, dict):
            session_constraints = request.metadata.get("session_constraints")

        # Show "building context" status (if enabled)
        if self.settings.STREAM_SHOW_THINKING:
            yield self._send_status_chunk(request_id, request.model, "Building context from history...")

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

        # Show "querying LM Studio" status (if enabled)
        if self.settings.STREAM_SHOW_THINKING:
            yield self._send_status_chunk(request_id, request.model, "Generating response...")

        # Convert to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(final_messages)

        # Accumulate full response for history
        full_content = ""

        try:
            # Stream from LM Studio using OpenAI client
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=openai_messages,
                temperature=request.temperature or self.settings.MODEL_TEMPERATURE,
                max_tokens=request.max_tokens or self.settings.MODEL_MAX_OUTPUT_TOKENS,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=True
            )

            # Process the stream
            async for chunk in stream:
                # Extract content from the chunk
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta_content = choice.delta.content if choice.delta and choice.delta.content else None
                    finish_reason = choice.finish_reason

                    # Build our response chunk
                    response_chunk = ChatCompletionChunk(
                        id=chunk.id if hasattr(chunk, 'id') else request_id,
                        created=chunk.created if hasattr(chunk, 'created') else int(time.time()),
                        model=request.model,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=0,
                                delta=ChatCompletionChunkDelta(
                                    role=ChatRole.ASSISTANT if delta_content else None,
                                    content=delta_content
                                ),
                                finish_reason=finish_reason
                            )
                        ]
                    )

                    # Accumulate content for history
                    if delta_content:
                        full_content += delta_content

                    yield response_chunk

            # After streaming completes, persist to history
            try:
                last_user = None
                for m in reversed(provided_messages):
                    if m.role == ChatRole.USER and (m.content or "").strip():
                        last_user = m
                        break

                assistant_msg = ResponseChatMessage(role=ChatRole.ASSISTANT, content=full_content)
                to_save = []
                if last_user is not None:
                    to_save.append(last_user)
                to_save.append(assistant_msg)
                await self.history_store.append(conversation_id, to_save)

            except Exception as ex:
                logger.debug(f"History persistence failed during streaming: {ex}")

        except Exception as e:
            logger.exception(f"[{request_id}] Streaming error from LM Studio")
            raise ValueError(f"LM Studio streaming error: {str(e)}")
    
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
