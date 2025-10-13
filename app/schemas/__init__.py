# Auth schemas
from .auth_request import *
from .auth_response import *

# OpenAI-compatible schemas
from .chat_requests import *
from .chat_responses import *
from .embedding import *
from .retrieval import *
from .common import *

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "SignUpRequest",
    "SignUpResponse",
    "RefreshTokenRequest",
    "UserPublic",
    "AuthTokens",
    
    # Chat Completion
    "ChatRole",
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChoice",
    "ChatCompletionChunk",
    "ChatCompletionChunkChoice",
    "ChatCompletionChunkDelta",
    "FunctionDefinition",
    "ToolDefinition",
    "ResponseFormat",
    "StreamOptions",
    "Usage",
    
    # Embeddings
    "EmbeddingRequest",
    "EmbeddingResponse",
    "Embedding",
    "EmbeddingUsage",
    
    # Retrieval/RAG
    "RetrievalMode",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievedDocument",
    "DocumentMetadata",
    "RAGRequest",
    "RAGResponse",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "DocumentDeleteRequest",
    "DocumentDeleteResponse",
    
    # Common
    "ErrorResponse",
    "ErrorDetail",
    "Model",
    "ModelListResponse",
    "DeleteResponse",
    "HealthCheckResponse",
]