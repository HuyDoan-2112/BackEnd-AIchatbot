from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.models.project_chat_link import ProjectChatLink
from app.models.project_document_link import ProjectDocumentLink
from app.models.project_model import Project
from app.models.chat_model import Chat
from app.models.document_model import Document


class LinkRepository:
    """
    Repository to manage links between Projects ↔ Chats and Projects ↔ Documents.
    Handles adding, removing, and fetching linked resources.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------
    # ✅ CHAT ↔ PROJECT LINKS
    # ------------------------------------------------------------
    async def link_chat_to_project(self, project_id: str, chat_id: str):
        """
        Link an existing chat to a project.
        Avoid duplicate links.
        """
        # Check if link already exists
        result = await self.db.execute(
            select(ProjectChatLink).where(
                and_(
                    ProjectChatLink.project_id == project_id,
                    ProjectChatLink.chat_id == chat_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # Already linked

        link = ProjectChatLink(project_id=project_id, chat_id=chat_id)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def unlink_chat_from_project(self, project_id: str, chat_id: str) -> bool:
        """
        Remove a chat from a project.
        """
        stmt = delete(ProjectChatLink).where(
            and_(
                ProjectChatLink.project_id == project_id,
                ProjectChatLink.chat_id == chat_id
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_chats_by_project(self, project_id: str):
        """
        Get all chat records linked to a specific project.
        """
        query = await self.db.execute(
            select(ProjectChatLink).where(ProjectChatLink.project_id == project_id)
        )
        links = query.scalars().all()

        # Optionally load full Chat objects
        chat_ids = [link.chat_id for link in links]
        if not chat_ids:
            return []

        chat_query = await self.db.execute(select(Chat).where(Chat.conversation_id.in_(chat_ids)))
        return chat_query.scalars().all()

    # ------------------------------------------------------------
    # ✅ DOCUMENT ↔ PROJECT LINKS
    # ------------------------------------------------------------
    async def link_document_to_project(self, project_id: str, document_id: str):
        """
        Link an existing document to a project.
        Avoid duplicate links.
        """
        result = await self.db.execute(
            select(ProjectDocumentLink).where(
                and_(
                    ProjectDocumentLink.project_id == project_id,
                    ProjectDocumentLink.document_id == document_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        link = ProjectDocumentLink(project_id=project_id, document_id=document_id)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def unlink_document_from_project(self, project_id: str, document_id: str) -> bool:
        """
        Remove a document from a project.
        """
        stmt = delete(ProjectDocumentLink).where(
            and_(
                ProjectDocumentLink.project_id == project_id,
                ProjectDocumentLink.document_id == document_id
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_documents_by_project(self, project_id: str):
        """
        Get all document records linked to a specific project.
        """
        query = await self.db.execute(
            select(ProjectDocumentLink).where(ProjectDocumentLink.project_id == project_id)
        )
        links = query.scalars().all()

        # Optionally load full Document objects
        doc_ids = [link.document_id for link in links]
        if not doc_ids:
            return []

        doc_query = await self.db.execute(select(Document).where(Document.id.in_(doc_ids)))
        return doc_query.scalars().all()
