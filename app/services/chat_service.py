from typing import AsyncGenerator, Optional, Dict, Any, List
from uuid import uuid4, UUID
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
from app.repository.chat_repository import ChatRepository
from app.core.response_status import ResponseStatus
from app.models.message_model import Message

logger = logging.getLogger(__name__)
class ChatService:
    """Handles logic for chat completion requests using LM Studio (OpenAI-compatible API)."""

    def __init__(self, llm_repository=None):
        self.llm_repository = llm_repository or default_llm_repo
        self.settings = get_settings()
        self.history_store = getattr(self.llm_repository, "history_store", InMemoryHistoryStore())
        self.tokenizer = Tokenizer(self.settings.MODEL_NAME)
        self.cache_service = get_cache_service()
        self.chat_repository = ChatRepository()
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
    
    # Helper function for a proper model when client call it.
    
    async def _get_client_for_model(self, model_id: str) -> AsyncOpenAI:
        """
        Dynamically create an OpenAI-compatible client for a specific model,
        using its base_url from the ModelRegistry.
        """
        registry1 = get_model_registry()
        model_config = registry1.get_chat_model(model_id)
        base_url = model_config.get("base_url", self.settings.MODEL_BASE_URL)
        api_key = model_config.get("api_key", self.settings.OPENAI_API_KEY or "lm-studio")
        
        # Reuse the same optimized HTTP client
        http_client =self.client._client if hasattr(self, "client") else httpx.AsyncClient(http2=True)
        return AsyncOpenAI(base_url=base_url, api_key=api_key, http_client=http_client)
    

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

    async def _get_or_create_conversation(self, request: ChatCompletionRequest) -> str:
        """
        Ensure a conversation identifier exists for the request.

        Anonymous users (no project context) receive an ephemeral conversation id and
        we skip database persistence. Authenticated requests with a project_id create
        or reuse a persisted conversation record.
        """
        metadata = dict(request.metadata or {})
        candidate_id = metadata.get("conversation_id") or metadata.get("session_id")

        # Determine whether this request should persist conversation history
        persist_flag = metadata.get("persist_conversation")
        if isinstance(persist_flag, str):
            persist_conversation = persist_flag.lower() in {"1", "true", "yes", "on"}
        elif persist_flag is None:
            persist_conversation = bool(metadata.get("project_id"))
        else:
            persist_conversation = bool(persist_flag)

        if not persist_conversation:
            # Ephemeral conversation: reuse provided identifier or create a new one.
            conversation_id = str(candidate_id) if candidate_id else str(uuid4())
            metadata["conversation_id"] = conversation_id
            metadata["persist_conversation"] = False
            request.metadata = metadata
            logger.debug("Using ephemeral conversation %s (no project context provided)", conversation_id)
            return conversation_id

        conversation_id: Optional[str] = None
        project_uuid: Optional[str] = None
        if candidate_id:
            try:
                conversation_uuid = str(UUID(str(candidate_id)))
                existing = await self.chat_repository.get_chat_by_id(conversation_uuid)
                if isinstance(existing, ResponseStatus):
                    if existing.success:
                        data = getattr(existing, "data", None) or {}
                        conversation_id = data.get("conversation_id")
                    else:
                        conversation_id = None
                else:
                    conversation_id = conversation_uuid
            except ValueError:
                logger.debug("Invalid persisted conversation_id provided; will create a new one.")

        if not conversation_id:
            project_id = metadata.get("project_id")
            if not project_id:
                raise ValueError("project_id is required in metadata to persist chat history")

            try:
                project_uuid = str(UUID(str(project_id)))
            except ValueError:
                raise ValueError("project_id metadata must be a valid UUID")

            company_id = metadata.get("company_id")
            title = metadata.get("conversation_title") or metadata.get("title")
            preset_id = metadata.get("preset_id")

            creation = await self.chat_repository.create_chat(
                company_id=company_id,
                project_id=project_uuid,
                title=title,
                created_by=request.user,
                model=request.model,
                preset_id=preset_id,
            )

            if isinstance(creation, ResponseStatus):
                if not creation.success:
                    logger.error(f"Failed to create conversation: {creation.message}")
                    raise ValueError(creation.message)
                payload = creation.data or {}
                conversation_id = payload.get("conversation_id")
            else:
                conversation_id = str(creation.conversation_id)

            logger.info(
                "Created conversation %s (user: %s, project: %s)",
                conversation_id,
                request.user or "anonymous",
                project_uuid,
            )

        if not conversation_id:
            raise ValueError("Failed to resolve conversation identifier.")

        metadata["conversation_id"] = conversation_id
        if project_uuid:
            metadata["project_id"] = project_uuid
        metadata["persist_conversation"] = True
        request.metadata = metadata
        return conversation_id

    async def _register_participant(self, conversation_id: str, user_id: Optional[str]) -> None:
        if not user_id:
            return
        try:
            result = await self.chat_repository.add_participant(conversation_id, user_id)
            if isinstance(result, ResponseStatus) and not result.success:
                logger.debug(f"Failed to register participant: {result.message}")
        except Exception as exc:
            logger.debug(f"Participant registration failed: {exc}")

    async def _persist_exchange(
        self,
        *,
        conversation_id: str,
        request: ChatCompletionRequest,
        user_message: Optional[ResponseChatMessage],
        assistant_message: ResponseChatMessage,
        usage: Usage,
    ) -> None:
        metadata = request.metadata or {}
        persist_flag = metadata.get("persist_conversation")
        if isinstance(persist_flag, str):
            persist_conversation = persist_flag.lower() in {"1", "true", "yes", "on"}
        elif persist_flag is None:
            persist_conversation = bool(metadata.get("project_id"))
        else:
            persist_conversation = bool(persist_flag)

        if not persist_conversation:
            logger.debug("Skipping persistence for conversation %s (ephemeral session)", conversation_id)
            return

        try:
            await self._register_participant(conversation_id, request.user)

            user_record = None
            if user_message and user_message.content:
                created = await self.chat_repository.create_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message.content,
                    author_user_id=request.user,
                    model_label=request.model,
                    temperature=request.temperature,
                    top_p=request.top_p,
                )
                if isinstance(created, Message):
                    user_record = created
                elif isinstance(created, ResponseStatus) and not created.success:
                    logger.debug(f"Failed to persist user message: {created.message}")

            assistant_record = await self.chat_repository.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message.content or "",
                author_user_id=None,
                parent_message_id=str(user_record.id) if user_record else None,
                model_label=request.model,
                temperature=request.temperature,
                top_p=request.top_p,
            )

            assistant_message_id: Optional[str] = None
            if isinstance(assistant_record, Message):
                assistant_message_id = str(assistant_record.id)
            elif isinstance(assistant_record, ResponseStatus):
                if assistant_record.success and assistant_record.data:
                    assistant_message_id = assistant_record.data.get("message_id")
                else:
                    logger.debug(f"Failed to persist assistant message: {assistant_record.message}")

            if assistant_message_id:
                usage_result = await self.chat_repository.save_message_usage(
                    assistant_message_id,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    latency_ms=None,
                    cost_usd=None,
                )
                if isinstance(usage_result, ResponseStatus) and not usage_result.success:
                    logger.debug(f"Failed to persist usage: {usage_result.message}")
        except Exception as exc:
            logger.error(f"Message persistence failed: {exc}", exc_info=True)

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

        # Determine conversation key (persisted conversation model)
        conversation_id = await self._get_or_create_conversation(request)

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
            client = await self._get_client_for_model(request.model)
            response = await client.chat.completions.create(
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

        # Compute usage
        if hasattr(response, 'usage') and response.usage:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        else:
            prompt_tokens = self.tokenizer.count_messages(final_messages)
            completion_tokens = self.tokenizer.count_text(assistant_content)
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )

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

            await self._persist_exchange(
                conversation_id=conversation_id,
                request=request,
                user_message=last_user,
                assistant_message=assistant_msg,
                usage=usage,
            )

            # Update rolling summary asynchronously (do not block response)
            # Note: We can't pass LangChain model here anymore, need to refactor summary if needed
            # asyncio.create_task(self.context_engine.update_summary(chat_model, conversation_id=conversation_id))
        except Exception as ex:
            logger.debug(f"History persistence failed: {ex}")
        timings["history_save"] = time.time() - history_start

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
                        content=f"_[{status_message}]_\n"  # Markdown italic for status
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
        conversation_id = await self._get_or_create_conversation(request)
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
            client = await self._get_client_for_model(request.model)
            stream = await client.chat.completions.create(
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

            # After streaming completes, persist to history and repository
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

                usage = Usage(
                    prompt_tokens=self.tokenizer.count_messages(final_messages),
                    completion_tokens=self.tokenizer.count_text(full_content),
                    total_tokens=self.tokenizer.count_messages(final_messages) + self.tokenizer.count_text(full_content),
                )
                await self._persist_exchange(
                    conversation_id=conversation_id,
                    request=request,
                    user_message=last_user,
                    assistant_message=assistant_msg,
                    usage=usage,
                )

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

    async def get_chat_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chat conversation details by ID."""
        result = await self.chat_repository.get_chat_by_id(conversation_id)
        if isinstance(result, ResponseStatus):
            if result.success:
                return result.data
            else:
                return None
        elif isinstance(result, dict):
            return result
        return None

    async def list_user_conversations(
        self,
        user_id: str,
        *,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 50,
    ) -> ResponseStatus:
        try:
            result = await self.chat_repository.list_chats_for_user(
                user_id,
                project_id=project_id,
                company_id=company_id,
                limit=limit,
            )
            if isinstance(result, ResponseStatus):
                return result
            return ResponseStatus(message="OK", data=result)
        except Exception as e:
            return ResponseStatus(message=f"Failed to list conversations: {e}", status_code=500)

    async def get_conversation_details(
        self, conversation_id: str, user_id: Optional[str] = None
    ) -> ResponseStatus:
        try:
            if user_id:
                has_access = await self.chat_repository.user_has_access(conversation_id, user_id)
                if not has_access:
                    return ResponseStatus(message="Forbidden", status_code=403)

            result = await self.chat_repository.get_chat_by_id(conversation_id)
            if isinstance(result, ResponseStatus):
                return result
            if result is None:
                return ResponseStatus(message="Not Found", status_code=404)
            return ResponseStatus(message="OK", data=result)
        except Exception as e:
            return ResponseStatus(message=f"Failed to get conversation: {e}", status_code=500)

    async def get_conversation_messages(
        self,
        conversation_id: str,
        *,
        user_id: Optional[str] = None,
        limit: int = 100,
        include_children: bool = False,
        include_artifacts: bool = False,
        include_usage: bool = False,
    ) -> ResponseStatus:
        try:
            if user_id:
                has_access = await self.chat_repository.user_has_access(conversation_id, user_id)
                if not has_access:
                    return ResponseStatus(message="Forbidden", status_code=403)

            result = await self.chat_repository.list_messages(
                conversation_id,
                limit=limit,
                include_children=include_children,
                include_artifacts=include_artifacts,
                include_usage=include_usage,
            )
            if isinstance(result, ResponseStatus):
                return result
            return ResponseStatus(message="OK", data=result)
        except Exception as e:
            return ResponseStatus(message=f"Failed to list messages: {e}", status_code=500)

_chat_service: Optional[ChatService] = None

def get_chat_service() -> ChatService:
    """Lazy singleton getter to avoid premature initialization before app startup."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
