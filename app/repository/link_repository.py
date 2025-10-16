from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.project_model import Project
from app.models.conversation_model import Conversation
from app.models.document_model import Document


class LinkRepository:
    """
    Repository to manage direct relationships between Projects, Conversations, and Documents.
    Since we now use direct foreign keys instead of join tables, this simplifies to basic queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------
    # ✅ CONVERSATION ↔ PROJECT (Direct FK)
    # ------------------------------------------------------------
    async def get_conversations_by_project(self, project_id: str):
        """
        Get all conversations for a specific project.
        """
        query = await self.db.execute(
            select(Conversation).where(Conversation.project_id == project_id)
        )
        return query.scalars().all()

    async def update_conversation_project(self, conversation_id: str, project_id: str):
        """
        Update a conversation's project_id (move to different project).
        """
        stmt = update(Conversation).where(
            Conversation.conversation_id == conversation_id
        ).values(project_id=project_id)
        await self.db.execute(stmt)
        await self.db.commit()

    # ------------------------------------------------------------
    # ✅ DOCUMENT ↔ PROJECT (Direct FK)
    # ------------------------------------------------------------
    async def get_documents_by_project(self, project_id: str):
        """
        Get all documents for a specific project.
        """
        query = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        return query.scalars().all()

    async def update_document_project(self, document_id: str, project_id: str):
        """
        Update a document's project_id (move to different project).
        """
        stmt = update(Document).where(
            Document.id == document_id
        ).values(project_id=project_id)
        await self.db.execute(stmt)
        await self.db.commit()
