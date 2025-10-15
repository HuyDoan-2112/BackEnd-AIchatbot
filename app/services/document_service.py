"""
Service layer for document operations.
"""
from typing import Union, Optional, List

from app.core.response_status import ResponseStatus, OK, InternalError, NotFound
from app.db.postgresql import get_db_connection
from app.repository.document_repository import DocumentRepository
from app.repository.link_repository import LinkRepository

from langchain.schema import Document

from app.db.vector_store import AsyncPgVector, ExtendedPgVector
from app.models.document_model import DocumentCreate


class DocumentService:
    """Service for managing documents in the vector store."""

    def __init__(self, vector_store: Union[ExtendedPgVector, AsyncPgVector]):
        self.vector_store = vector_store
        self._db_connection = None

    def _get_db(self):
        if self._db_connection is None:
            self._db_connection = get_db_connection()
        return self._db_connection

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

    # ------------------------------------------------------------------
    # Metadata management (PostgreSQL models)
    # ------------------------------------------------------------------
    async def create_document_record(
        self,
        *,
        title: str,
        content: str,
        uploaded_by: str,
        company_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = DocumentRepository(session)
                link_repo = LinkRepository(session)

                record = await repo.create_document(
                    title=title,
                    content=content,
                    uploaded_by=uploaded_by,
                    company_id=company_id,
                )

                if project_ids:
                    for project_id in project_ids:
                        await link_repo.link_document_to_project(str(record.id), project_id)

                payload = {
                    "id": str(record.id),
                    "title": record.title,
                    "company_id": str(record.company_id) if record.company_id else None,
                    "uploaded_by": str(record.uploaded_by) if record.uploaded_by else None,
                    "created_at": record.created_at,
                }
                return OK(message="Document record created", data=payload)
        except Exception as exc:
            return InternalError(message=f"Failed to create document record: {exc}")

    async def list_documents_by_project(self, project_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = DocumentRepository(session)
                records = await repo.list_documents_by_project(project_id)
                data = [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "company_id": str(doc.company_id) if doc.company_id else None,
                        "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None,
                        "created_at": doc.created_at,
                    }
                    for doc in records
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list project documents: {exc}")

    async def list_documents_by_company(self, company_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = DocumentRepository(session)
                records = await repo.list_documents_by_company(company_id)
                data = [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None,
                        "created_at": doc.created_at,
                    }
                    for doc in records
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list company documents: {exc}")

    async def delete_document_record(self, document_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = DocumentRepository(session)
                removed = await repo.delete_document(document_id)
                if not removed:
                    return NotFound(message="Document not found", error_code="4004")
                return OK(message="Document record deleted")
        except Exception as exc:
            return InternalError(message=f"Failed to delete document record: {exc}")
