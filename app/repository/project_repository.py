from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project_model import Project
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
            "organization_id": str(project.organization_id) if project.organization_id else None,
            "rag_enabled": project.rag_enabled,
            "rag_vector_store_id": project.rag_vector_store_id,
            "default_model": project.default_model,
            "system_prompt": project.system_prompt,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        if include_relations:
            payload["conversation_count"] = len(project.conversations) if project.conversations else 0
            payload["document_count"] = len(project.documents) if project.documents else 0
        return payload

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    async def create_project(
        self,
        *,
        name: str,
        organization_id: str,
        created_by: Optional[str],
        description: Optional[str] = None,
        rag_enabled: bool = True,
        rag_vector_store_id: Optional[str] = None,
        rag_chunk_size: int = 1000,
        rag_chunk_overlap: int = 200,
        rag_config: Optional[dict] = None,
        rules: Optional[dict] = None,
        default_model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            created_by=created_by,
            organization_id=organization_id,
            rag_enabled=rag_enabled,
            rag_vector_store_id=rag_vector_store_id,
            rag_chunk_size=rag_chunk_size,
            rag_chunk_overlap=rag_chunk_overlap,
            rag_config=rag_config,
            rules=rules,
            default_model=default_model,
            system_prompt=system_prompt,
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
                selectinload(Project.conversations),
                selectinload(Project.documents),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        *,
        organization_id: Optional[str] = None,
        limit: int = 100,
        with_relations: bool = False,
    ) -> List[Project]:
        stmt = (
            select(Project)
            .order_by(Project.start_date.desc())
            .limit(limit)
        )
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        if with_relations:
            stmt = stmt.options(
                selectinload(Project.conversations),
                selectinload(Project.documents),
            )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_project(
        self,
        project_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rag_enabled: Optional[bool] = None,
        rag_config: Optional[dict] = None,
        rules: Optional[dict] = None,
        default_model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[Project]:
        changes: Dict[str, Any] = {}
        if name is not None:
            changes["name"] = name
        if description is not None:
            changes["description"] = description
        if rag_enabled is not None:
            changes["rag_enabled"] = rag_enabled
        if rag_config is not None:
            changes["rag_config"] = rag_config
        if rules is not None:
            changes["rules"] = rules
        if default_model is not None:
            changes["default_model"] = default_model
        if system_prompt is not None:
            changes["system_prompt"] = system_prompt
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
    # Convenience helpers for accessing linked resources (Direct FK now!)
    # ------------------------------------------------------------------
    async def get_project_conversations(self, project_id: str) -> List[Conversation]:
        """Get all conversations for a project (direct relationship)."""
        stmt = (
            select(Conversation)
            .where(Conversation.project_id == project_id)
            .order_by(Conversation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_documents(self, project_id: str) -> List[Document]:
        """Get all documents for a project (direct relationship)."""
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
