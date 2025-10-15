from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.models.project_conversation import ProjectConversation
from app.models.project_document import ProjectDocument
from app.models.project_model import Project
from app.models.conversation_model import Conversation
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
    async def link_chat_to_project(self, project_id: str, conversation_id: str):
        """
        Link an existing chat to a project.
        Avoid duplicate links.
        """
        # Check if link already exists
        result = await self.db.execute(
            select(ProjectConversation).where(
                and_(
                    ProjectConversation.project_id == project_id,
                    ProjectConversation.conversation_id == conversation_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # Already linked

        link = ProjectConversation(project_id=project_id, conversation_id=conversation_id)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def unlink_chat_from_project(self, project_id: str, conversation_id: str) -> bool:
        """
        Remove a chat from a project.
        """
        stmt = delete(ProjectConversation).where(
            and_(
                ProjectConversation.project_id == project_id,
                ProjectConversation.conversation_id == conversation_id
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
            select(ProjectConversation).where(ProjectConversation.project_id == project_id)
        )
        links = query.scalars().all()

        # Optionally load full Chat objects
        conversation_ids = [link.conversation_id for link in links]
        if not conversation_ids:
            return []

        chat_query = await self.db.execute(
            select(Conversation).where(Conversation.conversation_id.in_(conversation_ids))
        )
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
            select(ProjectDocument).where(
                and_(
                    ProjectDocument.project_id == project_id,
                    ProjectDocument.document_id == document_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        link = ProjectDocument(project_id=project_id, document_id=document_id)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def unlink_document_from_project(self, project_id: str, document_id: str) -> bool:
        """
        Remove a document from a project.
        """
        stmt = delete(ProjectDocument).where(
            and_(
                ProjectDocument.project_id == project_id,
                ProjectDocument.document_id == document_id
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
            select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        )
        links = query.scalars().all()

        # Optionally load full Document objects
        doc_ids = [link.document_id for link in links]
        if not doc_ids:
            return []

        doc_query = await self.db.execute(select(Document).where(Document.id.in_(doc_ids)))
        return doc_query.scalars().all()
