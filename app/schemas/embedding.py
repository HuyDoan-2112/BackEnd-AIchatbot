"""
OpenAI-compatible Embeddings Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Union


class EmbeddingRequest(BaseModel):
    """OpenAI-compatible embeddings request"""
    # Required fields
    model: str = Field(..., description="ID of the model to use")
    input: Union[str, List[str], List[int], List[List[int]]] = Field(
        ...,
        description="Input text(s) to embed"
    )
    
    # Optional fields
    encoding_format: Optional[Literal["float", "base64"]] = Field(
        "float",
        description="Encoding format for embeddings"
    )
    dimensions: Optional[int] = Field(
        None,
        ge=1,
        description="Number of dimensions for embeddings (if supported)"
    )
    user: Optional[str] = Field(
        None,
        description="Unique user identifier"
    )

    @field_validator("input")
    @classmethod
    def validate_input(cls, v):
        """Validate input format"""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Input string cannot be empty")
        elif isinstance(v, list):
            if len(v) == 0:
                raise ValueError("Input list cannot be empty")
            # Check if it's a list of strings
            if all(isinstance(item, str) for item in v):
                for item in v:
                    if not item.strip():
                        raise ValueError("Input strings cannot be empty")
        return v


class Embedding(BaseModel):
    """Single embedding object"""
    object: Literal["embedding"] = "embedding"
    embedding: Union[List[float], str]  # List[float] for float, str for base64
    index: int


class EmbeddingUsage(BaseModel):
    """Embedding usage statistics"""
    prompt_tokens: int
    total_tokens: int


class EmbeddingResponse(BaseModel):
    """OpenAI-compatible embeddings response"""
    object: Literal["list"] = "list"
    data: List[Embedding]
    model: str
    usage: EmbeddingUsage
