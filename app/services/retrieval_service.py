from __future__ import annotations

from typing import AsyncGenerator, Dict, Any, List, Optional
import asyncio

from app.core.config import get_settings
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RAGRequest,
    RAGResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
)

try:  # Optional dependency
    from qdrant_client import QdrantClient  # type: ignore
except Exception:  # pragma: no cover - optional
    QdrantClient = None  # type: ignore

try:
    from langchain_openai import OpenAIEmbeddings  # type: ignore
except Exception:  # pragma: no cover - optional
    OpenAIEmbeddings = None  # type: ignore


class QdrantRetriever:
    """
    Enhanced Qdrant retriever with project-based filtering support.
    Uses OpenAI embeddings via langchain-openai.
    If dependencies or config are missing, returns an empty result gracefully.
    """

    def __init__(
        self,
        host: str = "http://localhost:6333",
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        top_k: int = 3,
    ) -> None:
        self.collection_name = collection_name
        self._top_k = max(1, top_k)

        # Create clients if possible
        self._qdrant = None
        if QdrantClient is not None:
            try:
                self._qdrant = QdrantClient(url=host)
            except Exception:
                self._qdrant = None

        self._embedder = None
        if OpenAIEmbeddings is not None and embedding_model:
            try:
                kwargs = {
                    "model": embedding_model,
                    "api_key": openai_api_key,
                }
                if base_url:
                    kwargs["base_url"] = base_url
                self._embedder = OpenAIEmbeddings(**kwargs)  # type: ignore[arg-type]
            except Exception:
                self._embedder = None

    async def asearch(
        self,
        query: str,
        k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Search with optional metadata filtering.

        Args:
            query: Search query text
            k: Number of results to return
            filters: Optional metadata filters
                Example: {"project_id": "uuid-123", "user_id": "uuid-456"}

        Returns:
            List of document text chunks
        """
        limit = k or self._top_k
        if not query or not self.collection_name or self._qdrant is None or self._embedder is None:
            return []

        # Embed query (sync embed in a thread to avoid blocking event loop)
        try:
            vector = await asyncio.to_thread(self._embedder.embed_query, query)  # type: ignore
        except Exception:
            return []

        try:
            # Build Qdrant filter if provided
            qdrant_filter = None
            if filters:
                try:
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    conditions = []
                    for key, value in filters.items():
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=str(value))
                            )
                        )
                    qdrant_filter = Filter(must=conditions)
                except Exception:
                    pass  # If filter creation fails, search without filters

            results = await asyncio.to_thread(
                self._qdrant.search,
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=qdrant_filter,
                limit=limit,
            )
        except Exception:
            return []

        docs: List[str] = []
        for r in results:
            payload = getattr(r, "payload", None) or {}
            # Try common payload keys
            text = (
                payload.get("text")
                or payload.get("content")
                or payload.get("chunk")
                or payload.get("document")
            )
            if text and isinstance(text, str):
                docs.append(text)

        return docs


def build_default_retriever() -> QdrantRetriever:
    """Build a QdrantRetriever with default settings from config."""
    settings = get_settings()
    return QdrantRetriever(
        host=getattr(settings, "RETRIEVAL_HOST", "http://localhost:6333"),
        collection_name=getattr(settings, "COLLECTION_NAME", None),
        embedding_model=getattr(settings, "EMBEDDING_MODEL_NAME", None),
        openai_api_key=getattr(settings, "OPENAI_API_KEY", None),
        base_url=getattr(settings, "EMBEDDING_BASE_URL", None),
        top_k=getattr(settings, "RETRIEVAL_TOP_K", 3),
    )


class RetrievalService:
    """Service for document retrieval and RAG operations."""
    
    def __init__(self, vector_repository, embedding_repository):
        self.vector_repository = vector_repository
        self.embedding_repository = embedding_repository
    
    async def retrieve_documents(self, request: RetrievalRequest) -> RetrievalResponse:
        pass
    
    async def rag_query(self, request: RAGRequest) -> RAGResponse:
        pass
    
    async def rag_query_stream(self, request: RAGRequest) -> AsyncGenerator[str, None]:
        pass
        yield
    
    async def upload_document(self, request: DocumentUploadRequest) -> DocumentUploadResponse:
        pass
    
    async def delete_documents(self, request: DocumentDeleteRequest) -> DocumentDeleteResponse:
        pass
    
    async def split_document(self, content: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        pass
    
    async def construct_rag_prompt(self, query: str, documents: List[Dict[str, Any]], system_prompt: str = None) -> str:
        pass


retrieval_service = RetrievalService(vector_repository=None, embedding_repository=None)
