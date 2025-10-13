from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Dict, Any, Literal, Optional, Union
import re

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Optional[str] = Field(None, description="Text content of the message")
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: Optional[str], values):
        """Disallow empty messages except for role='tool'."""
        role = values.get("role")
        if role != "tool" and (v is None or not v.strip()):
            raise ValueError("Message content cannot be empty")
        return v


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Model name, e.g. gpt-4o-mini, mistral-7b")

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str):
        if not v.strip():
            raise ValueError("Model name cannot be blank")
        return v



class ChatRequest(BaseModel):
    """Request model for /v1/chat/completions"""
    model_config = ConfigDict(extra="forbid")

    models: Union[str, List[ModelConfig]] = Field(..., description="Model name or list of models")
    messages: List[ChatMessage] = Field(..., description="Conversation context or chat history")
    pipeline: Optional[str] = Field("default", description="Custom pipeline logic, e.g. rag, router, summarizer")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context continuation")
    stream: bool = Field(False, description="Enable SSE streaming mode")
    user: Optional[str] = Field(None, description="User ID or username sending request")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context metadata")

    # Default parameters
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(512, ge=1)
    top_p: Optional[float] = Field(1.0, ge=0, le=1)
    presence_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    stop: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_messages_and_model(self):
        """Ensure message list and model configuration are valid."""
        if not self.messages:
            raise ValueError("At least one message is required in chat request")

        if not any(m.role == "user" for m in self.messages):
            raise ValueError("Chat request must contain at least one 'user' message")

        if self.temperature is not None and not (0 <= self.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")

        return self
