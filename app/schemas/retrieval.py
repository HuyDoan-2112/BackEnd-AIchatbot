"""
OpenAI-compatible Retrieval/RAG Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class RetrievalMode(str, Enum):
    """Retrieval mode"""
    SIMILARITY = "similarity"
    MMR = "mmr"  # Maximal Marginal Relevance
    SIMILARITY_SCORE_THRESHOLD = "similarity_score_threshold"


class DocumentMetadata(BaseModel):
    """Document metadata"""
    source: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    score: Optional[float] = None
    additional_info: Optional[Dict[str, Any]] = None


class RetrievedDocument(BaseModel):
    """Retrieved document from vector store"""
    id: Optional[str] = None
    content: str
    metadata: Optional[DocumentMetadata] = None
    score: Optional[float] = None


class RetrievalRequest(BaseModel):
    """Request for document retrieval"""
    query: str = Field(..., min_length=1, description="Query text")
    k: Optional[int] = Field(4, ge=1, le=100, description="Number of documents to retrieve")
    filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    search_type: Optional[RetrievalMode] = Field(
        RetrievalMode.SIMILARITY,
        description="Search type"
    )
    score_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )
    
    # MMR-specific parameters
    fetch_k: Optional[int] = Field(
        20,
        ge=1,
        description="Number of documents to fetch for MMR"
    )
    lambda_mult: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Diversity parameter for MMR"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Validate query is not empty"""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class RetrievalResponse(BaseModel):
    """Response for document retrieval"""
    query: str
    documents: List[RetrievedDocument]
    count: int
    search_type: str


class RAGRequest(BaseModel):
    """Request for RAG (Retrieval-Augmented Generation)"""
    query: str = Field(..., min_length=1, description="User query")
    k: Optional[int] = Field(4, ge=1, le=20, description="Number of documents to retrieve")
    
    # Chat completion parameters
    model: Optional[str] = Field("gpt-3.5-turbo", description="LLM model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(False, description="Stream responses")
    
    # Retrieval parameters
    filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    search_type: Optional[RetrievalMode] = Field(
        RetrievalMode.SIMILARITY,
        description="Search type"
    )
    
    # System prompt customization
    system_prompt: Optional[str] = Field(
        None,
        description="Custom system prompt (will be combined with retrieved context)"
    )
    
    # Whether to include source documents in response
    include_sources: Optional[bool] = Field(True, description="Include source documents")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Validate query is not empty"""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class RAGResponse(BaseModel):
    """Response for RAG query"""
    answer: str
    sources: Optional[List[RetrievedDocument]] = None
    model: str
    usage: Optional[Dict[str, int]] = None


class DocumentUploadRequest(BaseModel):
    """Request for uploading documents"""
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")
    chunk_size: Optional[int] = Field(1000, ge=100, le=10000, description="Chunk size")
    chunk_overlap: Optional[int] = Field(200, ge=0, le=1000, description="Chunk overlap")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate content is not empty"""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    message: str
    document_ids: List[str]
    chunks_created: int
    metadata: Optional[Dict[str, Any]] = None


class DocumentDeleteRequest(BaseModel):
    """Request to delete documents"""
    ids: Optional[List[str]] = Field(None, description="Document IDs to delete")
    filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filter to delete matching documents")

    @field_validator("ids", "filter")
    @classmethod
    def validate_at_least_one(cls, v, info):
        """Ensure at least one of ids or filter is provided"""
        if info.field_name == "filter" and not v and not info.data.get("ids"):
            raise ValueError("Either 'ids' or 'filter' must be provided")
        return v


class DocumentDeleteResponse(BaseModel):
    """Response for document deletion"""
    message: str
    deleted_count: int
