from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.document_model import Document


class DocumentRepository:
    """
    Repository for managing Document CRUD operations and ownership checks.
    Supports both individual and company documents.
    """

    def __init__(self, db: AsyncSession):
        # DB session is injected from FastAPI or service layer
        self.db = db

    # ------------------------------------------------------------
    # ✅ CREATE
    # ------------------------------------------------------------
    async def create_document(
        self,
        title: str,
        content: str,
        uploaded_by: str,
        project_id: str,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
    ) -> Document:
        """
        Create and save a new document linked to a project.
        """
        document = Document(
            title=title,
            content=content,
            uploaded_by=uploaded_by,
            project_id=project_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    # ------------------------------------------------------------
    # ✅ READ
    # ------------------------------------------------------------
    async def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID.
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_documents_by_user(self, user_id: str) -> List[Document]:
        """
        Return all documents uploaded by a specific user (personal or company).
        """
        result = await self.db.execute(
            select(Document).where(Document.uploaded_by == user_id)
        )
        return result.scalars().all()

    async def list_documents_by_project(self, project_id: str) -> List[Document]:
        """
        Return all documents linked to a specific project.
        Documents now have direct FK to project.
        """
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        return result.scalars().all()

    async def search_documents(
        self, keyword: str, user_id: Optional[str] = None, company_id: Optional[str] = None
    ) -> List[Document]:
        """
        Search documents by title/content (case-insensitive).
        Supports combined filtering by user or company.
        """
        stmt = select(Document).where(
            or_(
                Document.title.ilike(f"%{keyword}%"),
                Document.content.ilike(f"%{keyword}%"),
            )
        )
        if company_id:
            stmt = stmt.where(Document.company_id == company_id)
        elif user_id:
            # Only personal documents or uploaded by this user
            stmt = stmt.where(
                or_(
                    Document.uploaded_by == user_id,
                    Document.company_id.is_(None),
                )
            )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------
    # ✅ UPDATE
    # ------------------------------------------------------------
    async def update_document_content(
        self, document_id: str, new_content: str
    ) -> Optional[Document]:
        """
        Update the content of a document.
        """
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(content=new_content)
            .returning(Document)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def rename_document(
        self, document_id: str, new_title: str
    ) -> Optional[Document]:
        """
        Rename a document by changing its title.
        """
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(title=new_title)
            .returning(Document)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    # ------------------------------------------------------------
    # ✅ DELETE
    # ------------------------------------------------------------
    async def delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a document by ID.
        Optionally verify the uploader (user_id) before deleting.
        """
        stmt = delete(Document).where(Document.id == document_id)
        if user_id:
            stmt = stmt.where(Document.uploaded_by == user_id)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------
    # ✅ VALIDATION / HELPERS
    # ------------------------------------------------------------
    async def document_exists(self, title: str, user_id: str) -> bool:
        """
        Check if a document with the same title already exists for this user.
        """
        query = await self.db.execute(
            select(Document).where(
                and_(Document.title == title, Document.uploaded_by == user_id)
            )
        )
        return query.scalar_one_or_none() is not None

    async def verify_user_access(self, document_id: str, user_id: str) -> bool:
        """
        Check if the document belongs to the given user.
        """
        query = await self.db.execute(
            select(Document).where(
                and_(
                    Document.id == document_id,
                    Document.uploaded_by == user_id,
                )
            )
        )
        return query.scalar_one_or_none() is not None

    async def verify_company_scope(self, document_id: str, company_id: str) -> bool:
        """
        Check if the document belongs to a specific company.
        """
        query = await self.db.execute(
            select(Document).where(
                and_(
                    Document.id == document_id,
                    Document.company_id == company_id,
                )
            )
        )
        return query.scalar_one_or_none() is not None
