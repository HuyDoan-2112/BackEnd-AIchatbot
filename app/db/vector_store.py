"""
Vector store implementations for document storage and retrieval.
"""
import asyncio
import time
from typing import Any, Optional

from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.documents import Document
from langchain_core.runnables.config import run_in_executor
from sqlalchemy.orm import Session


class ExtendedPgVector(PGVector):
    """Extended PGVector with additional methods for document management."""

    def get_all_ids(self) -> list[str]:
        """
        Get all document IDs from the vector store.

        TODO: Implement this method to retrieve all custom_ids from the database.
        - Use self._bind to get database connection
        - Query EmbeddingStore.custom_id
        - Return list of IDs
        """
        time.sleep(5)  # Simulate blocking I/O operation

        with Session(self._bind) as session:
            results = session.query(self.EmbeddingStore.custom_id).all()
            return [result[0] for result in results if result[0] is not None]

    def get_documents_by_ids(self, ids: list[str]) -> list[Document]:
        """
        Retrieve documents by their IDs.

        TODO: Implement this method to fetch documents by IDs.
        - Query EmbeddingStore filtered by custom_id
        - Convert results to Document objects
        - Return list of Documents
        """
        with Session(self._bind) as session:
            results = (
                session.query(self.EmbeddingStore)
                .filter(self.EmbeddingStore.custom_id.in_(ids))
                .all()
            )
            documents = [
                Document(page_content=result.page_content, metadata=result.metadata or {})
                for result in results
                if result.custom_id in ids
            ]
            return documents

    def delete_documents(self, ids: list[str]) -> None:
        """
        Delete documents by their IDs.

        TODO: Implement this method to delete documents from the vector store.
        - Call parent delete method with ids parameter
        """
        self.delete(ids=ids)


class AsyncPgVector(ExtendedPgVector):
    """Async wrapper for PGVector operations."""

    async def get_all_ids(self) -> list[str]:
        """
        Async version of get_all_ids.

        TODO: Implement async version using run_in_executor.
        - Add await asyncio.sleep for non-blocking delay
        - Wrap synchronous call with run_in_executor
        """
        await asyncio.sleep(5)  # Simulate non-blocking I/O
        return await run_in_executor(None, super().get_all_ids)

    async def get_documents_by_ids(self, ids: list[str]) -> list[Document]:
        """
        Async version of get_documents_by_ids.

        TODO: Implement async version using run_in_executor.
        """
        return await run_in_executor(None, super().get_documents_by_ids, ids)

    async def delete_documents(self, ids: list[str]) -> None:
        """
        Async version of delete_documents.

        TODO: Implement async version using run_in_executor.
        """
        await run_in_executor(None, super().delete_documents, ids)

    async def add_documents(self, documents: list[Document]) -> list[str]:
        """
        Async version of add_documents.

        TODO: Implement async version to add documents to the vector store.
        - Wrap parent add_documents method with run_in_executor
        - Return list of generated IDs
        """
        return await run_in_executor(None, super().add_documents, documents)
