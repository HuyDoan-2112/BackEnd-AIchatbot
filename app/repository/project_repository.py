from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project_model import Project
from app.models.project_conversation import ProjectConversation
from app.models.project_document import ProjectDocument
from app.models.conversation_model import Conversation
from app.models.document_model import Document


class ProjectRepository:
    """
    Repository for managing project entities and their linked resources.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def serialize_project(project: Project, include_relations: bool = True) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_by": str(project.created_by) if project.created_by else None,
            "company_id": str(project.company_id) if project.company_id else None,
            "start_date": project.start_date,
            "end_date": project.end_date,
        }
        if include_relations:
            payload["conversation_ids"] = [
                str(conv.conversation_id) for conv in project.conversation_links
            ]
            payload["document_ids"] = [
                str(link.document_id) for link in project.document_links
            ]
        return payload

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    async def create_project(
        self,
        *,
        name: str,
        company_id: str,
        created_by: Optional[str],
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            created_by=created_by,
            company_id=company_id,
            start_date=start_date or datetime.utcnow(),
            end_date=end_date,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: str, *, with_relations: bool = False) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id)
        if with_relations:
            stmt = stmt.options(
                selectinload(Project.conversation_links).selectinload(ProjectConversation.conversation),
                selectinload(Project.document_links).selectinload(ProjectDocument.document),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        *,
        company_id: Optional[str] = None,
        limit: int = 100,
        with_relations: bool = False,
    ) -> List[Project]:
        stmt = (
            select(Project)
            .order_by(Project.start_date.desc())
            .limit(limit)
        )
        if company_id:
            stmt = stmt.where(Project.company_id == company_id)
        if with_relations:
            stmt = stmt.options(
                selectinload(Project.conversation_links),
                selectinload(Project.document_links),
            )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_project(
        self,
        project_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[Project]:
        changes: Dict[str, Any] = {}
        if name is not None:
            changes["name"] = name
        if description is not None:
            changes["description"] = description
        if start_date is not None:
            changes["start_date"] = start_date
        if end_date is not None:
            changes["end_date"] = end_date

        if not changes:
            return await self.get_project(project_id, with_relations=False)

        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(**changes)
            .returning(Project)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_project(self, project_id: str) -> bool:
        stmt = delete(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Convenience helpers for accessing linked resources
    # ------------------------------------------------------------------
    async def get_project_conversations(self, project_id: str) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .join(ProjectConversation, ProjectConversation.conversation_id == Conversation.conversation_id)
            .where(ProjectConversation.project_id == project_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_documents(self, project_id: str) -> List[Document]:
        stmt = (
            select(Document)
            .join(ProjectDocument, ProjectDocument.document_id == Document.id)
            .where(ProjectDocument.project_id == project_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
