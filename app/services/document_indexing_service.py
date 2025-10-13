"""
Document Indexing Service for Qdrant
Implements company-based collection strategy with project-level filtering
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny

from app.core.config import get_settings


class DocumentIndexingService:
    """
    Manages document vectorization and indexing in Qdrant.
    Uses company-based collections with project-level metadata filtering.
    """

    def __init__(self, embedder=None):
        """
        Initialize the indexing service.

        Args:
            embedder: Embedding model (e.g., OpenAIEmbeddings)
        """
        self.settings = get_settings()
        self.qdrant = QdrantClient(url=self.settings.RETRIEVAL_HOST)
        self.embedder = embedder
        self.vector_size = 1536  # OpenAI embeddings dimension

    def _get_collection_name(self, company_id: UUID) -> str:
        """Generate collection name for a company."""
        return f"company_{str(company_id).replace('-', '_')}_documents"

    async def ensure_collection_exists(self, company_id: UUID) -> bool:
        """
        Create collection for company if it doesn't exist.

        Args:
            company_id: Company UUID

        Returns:
            True if collection exists or was created
        """
        collection_name = self._get_collection_name(company_id)

        try:
            # Check if collection exists
            collections = await asyncio.to_thread(self.qdrant.get_collections)
            collection_names = [c.name for c in collections.collections]

            if collection_name in collection_names:
                return True

            # Create new collection
            await asyncio.to_thread(
                self.qdrant.create_collection,
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

            # Create indexes for common filters
            await asyncio.to_thread(
                self.qdrant.create_payload_index,
                collection_name=collection_name,
                field_name="project_id",
                field_schema="keyword"
            )
            await asyncio.to_thread(
                self.qdrant.create_payload_index,
                collection_name=collection_name,
                field_name="document_id",
                field_schema="keyword"
            )

            return True

        except Exception as e:
            print(f"Error ensuring collection: {e}")
            return False

    async def index_document(
        self,
        company_id: UUID,
        document_id: UUID,
        project_id: UUID,
        uploaded_by: UUID,
        title: str,
        chunks: List[str],
        project_member_ids: List[UUID],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a document's chunks into Qdrant.

        Args:
            company_id: Company UUID
            document_id: Document UUID
            project_id: Project UUID this document belongs to
            uploaded_by: User UUID who uploaded
            title: Document title
            chunks: List of text chunks to index
            project_member_ids: List of user UUIDs who have access to this project
            metadata: Additional metadata (tags, type, etc.)

        Returns:
            True if indexing successful
        """
        if not self.embedder or not chunks:
            return False

        collection_name = self._get_collection_name(company_id)

        # Ensure collection exists
        await self.ensure_collection_exists(company_id)

        try:
            # Generate embeddings for all chunks
            vectors = await asyncio.to_thread(
                self.embedder.embed_documents,
                chunks
            )

            # Create points for each chunk
            points = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                point_id = f"{document_id}_chunk_{i}"

                payload = {
                    # Core identifiers
                    "company_id": str(company_id),
                    "document_id": str(document_id),
                    "project_id": str(project_id),
                    "uploaded_by": str(uploaded_by),

                    # Document info
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content": chunk,

                    # Access control
                    "project_members": [str(uid) for uid in project_member_ids],

                    # Timestamps
                    "indexed_at": datetime.utcnow().isoformat(),
                }

                # Add custom metadata
                if metadata:
                    payload.update(metadata)

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )

            # Upsert points to Qdrant
            await asyncio.to_thread(
                self.qdrant.upsert,
                collection_name=collection_name,
                points=points
            )

            return True

        except Exception as e:
            print(f"Error indexing document: {e}")
            return False

    async def search_project_documents(
        self,
        company_id: UUID,
        project_id: UUID,
        query: str,
        user_id: Optional[UUID] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search documents within a specific project.

        Args:
            company_id: Company UUID
            project_id: Project UUID to search within
            query: Search query text
            user_id: Optional user UUID for access verification
            limit: Maximum results to return

        Returns:
            List of search results with content and metadata
        """
        if not self.embedder:
            return []

        collection_name = self._get_collection_name(company_id)

        try:
            # Generate query embedding
            query_vector = await asyncio.to_thread(
                self.embedder.embed_query,
                query
            )

            # Build filter
            filter_conditions = [
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=str(project_id))
                )
            ]

            # Optional: verify user has access
            if user_id:
                filter_conditions.append(
                    FieldCondition(
                        key="project_members",
                        match=MatchAny(any=[str(user_id)])
                    )
                )

            # Search
            results = await asyncio.to_thread(
                self.qdrant.search,
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=Filter(must=filter_conditions),
                limit=limit,
                with_payload=True
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.payload.get("content", ""),
                    "title": result.payload.get("title", ""),
                    "document_id": result.payload.get("document_id"),
                    "chunk_index": result.payload.get("chunk_index"),
                    "score": result.score,
                    "metadata": result.payload
                })

            return formatted_results

        except Exception as e:
            print(f"Error searching documents: {e}")
            return []

    async def search_user_documents(
        self,
        company_id: UUID,
        user_id: UUID,
        project_ids: List[UUID],
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents across all user's projects.

        Args:
            company_id: Company UUID
            user_id: User UUID
            project_ids: List of project UUIDs user has access to
            query: Search query text
            limit: Maximum results to return

        Returns:
            List of search results with content and metadata
        """
        if not self.embedder or not project_ids:
            return []

        collection_name = self._get_collection_name(company_id)

        try:
            # Generate query embedding
            query_vector = await asyncio.to_thread(
                self.embedder.embed_query,
                query
            )

            # Build filter for multiple projects
            filter_conditions = [
                FieldCondition(
                    key="project_id",
                    match=MatchAny(any=[str(pid) for pid in project_ids])
                ),
                FieldCondition(
                    key="project_members",
                    match=MatchAny(any=[str(user_id)])
                )
            ]

            # Search
            results = await asyncio.to_thread(
                self.qdrant.search,
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=Filter(must=filter_conditions),
                limit=limit,
                with_payload=True
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.payload.get("content", ""),
                    "title": result.payload.get("title", ""),
                    "document_id": result.payload.get("document_id"),
                    "project_id": result.payload.get("project_id"),
                    "chunk_index": result.payload.get("chunk_index"),
                    "score": result.score,
                    "metadata": result.payload
                })

            return formatted_results

        except Exception as e:
            print(f"Error searching user documents: {e}")
            return []

    async def delete_document(
        self,
        company_id: UUID,
        document_id: UUID
    ) -> bool:
        """
        Delete all chunks of a document from Qdrant.

        Args:
            company_id: Company UUID
            document_id: Document UUID to delete

        Returns:
            True if deletion successful
        """
        collection_name = self._get_collection_name(company_id)

        try:
            # Delete by filter
            await asyncio.to_thread(
                self.qdrant.delete,
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(document_id))
                        )
                    ]
                )
            )
            return True

        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    async def delete_company_collection(self, company_id: UUID) -> bool:
        """
        Delete entire collection for a company.

        Args:
            company_id: Company UUID

        Returns:
            True if deletion successful
        """
        collection_name = self._get_collection_name(company_id)

        try:
            await asyncio.to_thread(
                self.qdrant.delete_collection,
                collection_name=collection_name
            )
            return True

        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False
