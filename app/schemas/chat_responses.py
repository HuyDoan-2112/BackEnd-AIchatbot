"""
OpenAI-compatible Chat Completion Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal, Union
from enum import Enum


class ChatRole(str, Enum):
    """Chat message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Individual chat message"""
    role: ChatRole
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v, info):
        """Ensure content is present for non-tool messages"""
        role = info.data.get("role")
        if role in [ChatRole.SYSTEM, ChatRole.USER] and not v:
            raise ValueError(f"Content is required for {role} messages")
        return v


class FunctionDefinition(BaseModel):
    """Function definition for function calling"""
    name: str = Field(..., description="Function name")
    description: Optional[str] = Field(None, description="Function description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Function parameters schema")


class ToolDefinition(BaseModel):
    """Tool definition"""
    type: Literal["function"] = "function"
    function: FunctionDefinition


class ResponseFormat(BaseModel):
    """Response format specification"""
    type: Literal["text", "json_object"] = "text"


class StreamOptions(BaseModel):
    """Streaming options"""
    include_usage: bool = Field(False, description="Include usage stats in stream")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    # Required fields
    model: str = Field(..., description="ID of the model to use")
    messages: List[ChatMessage] = Field(..., min_length=1, description="List of messages")
    
    # Optional fields
    temperature: Optional[float] = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    n: Optional[int] = Field(1, ge=1, le=10, description="Number of completions to generate")
    stream: Optional[bool] = Field(False, description="Stream responses")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    logit_bias: Optional[Dict[str, float]] = Field(None, description="Logit bias")
    user: Optional[str] = Field(None, description="Unique user identifier")
    
    # Custom metadata for context and conversation management
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for conversation context")
    
    # Function calling
    functions: Optional[List[FunctionDefinition]] = Field(None, description="Deprecated: use tools")
    function_call: Optional[Union[str, Dict[str, str]]] = Field(None, description="Deprecated: use tool_choice")
    tools: Optional[List[ToolDefinition]] = Field(None, description="Available tools")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(None, description="Tool choice")
    
    # Additional options
    response_format: Optional[ResponseFormat] = Field(None, description="Response format")
    seed: Optional[int] = Field(None, description="Random seed for deterministic generation")
    logprobs: Optional[bool] = Field(False, description="Return log probabilities")
    top_logprobs: Optional[int] = Field(None, ge=0, le=20, description="Number of top logprobs")
    stream_options: Optional[StreamOptions] = Field(None, description="Streaming options")


class Usage(BaseModel):
    """Token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    """Single completion choice"""
    index: int
    message: ChatMessage
    finish_reason: Optional[Literal["stop", "length", "function_call", "tool_calls", "content_filter"]] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None


class ChatCompletionChunkDelta(BaseModel):
    """Delta in streaming chunk"""
    role: Optional[ChatRole] = None
    content: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    """Choice in streaming chunk"""
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[Literal["stop", "length", "function_call", "tool_calls", "content_filter"]] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible streaming chunk"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
    system_fingerprint: Optional[str] = None
    usage: Optional[Usage] = None
