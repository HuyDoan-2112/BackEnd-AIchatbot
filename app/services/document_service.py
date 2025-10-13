"""
Service layer for document operations.
"""
from typing import Union

from langchain.schema import Document

from app.db.vector_store import AsyncPgVector, ExtendedPgVector
from app.models.document_models import DocumentCreate


class DocumentService:
    """Service for managing documents in the vector store."""

    def __init__(self, vector_store: Union[ExtendedPgVector, AsyncPgVector]):
        self.vector_store = vector_store

    async def add_documents(self, documents: list[DocumentCreate]) -> list[str]:
        """
        Add documents to the vector store.

        TODO: Implement this method to add documents.
        - Convert DocumentCreate models to LangChain Document objects
        - Add digest to metadata
        - Call vector store's add_documents method (handle both sync/async)
        - Return list of IDs
        """
        docs = [
            Document(
                page_content=doc.page_content,
                metadata={
                    **doc.metadata,
                    "digest": doc.generate_digest()
                } if doc.metadata else {"digest": doc.generate_digest()}
            ) for doc in documents
        ]

        if isinstance(self.vector_store, AsyncPgVector):
            ids = await self.vector_store.add_documents(docs)
        else:
            ids = self.vector_store.add_documents(docs)

        return ids

    async def get_all_ids(self) -> list[str]:
        """
        Get all document IDs.

        TODO: Implement this method to retrieve all IDs.
        - Call vector store's get_all_ids (handle both sync/async)
        - Return list of IDs
        """
        if isinstance(self.vector_store, AsyncPgVector):
            return await self.vector_store.get_all_ids()
        else:
            return self.vector_store.get_all_ids()

    async def get_documents_by_ids(self, ids: list[str]) -> list[Document]:
        """
        Get documents by their IDs.

        TODO: Implement this method to retrieve documents by IDs.
        - Validate IDs exist
        - Call vector store's get_documents_by_ids (handle both sync/async)
        - Return documents
        """
        if isinstance(self.vector_store, AsyncPgVector):
            return await self.vector_store.get_documents_by_ids(ids)
        else:
            return self.vector_store.get_documents_by_ids(ids)

    async def delete_documents(self, ids: list[str]) -> int:
        """
        Delete documents by their IDs.

        TODO: Implement this method to delete documents.
        - Validate IDs exist
        - Call vector store's delete_documents (handle both sync/async)
        - Return count of deleted documents
        """
        if isinstance(self.vector_store, AsyncPgVector):
            await self.vector_store.delete_documents(ids)
        else:
            self.vector_store.delete_documents(ids)

        return len(ids)

    async def validate_ids_exist(self, ids: list[str]) -> bool:
        """
        Validate that all IDs exist in the vector store.

        TODO: Implement this helper method.
        - Get all existing IDs
        - Check if all requested IDs are in existing IDs
        - Return boolean
        """
        existing_ids = await self.get_all_ids()
        return all(id in existing_ids for id in ids)
