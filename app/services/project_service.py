from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.postgresql import get_db_connection
from app.repository.project_repository import ProjectRepository
from app.repository.document_repository import DocumentRepository
from app.core.response_status import ResponseStatus, OK, NotFound, InternalError


class ProjectService:
    """
    Service layer for project management, orchestrating project CRUD and
    relationship operations (conversations, documents).
    """

    def __init__(self):
        self._db_connection = None

    def _get_db(self):
        if self._db_connection is None:
            self._db_connection = get_db_connection()
        return self._db_connection

    async def create_project(
        self,
        *,
        name: str,
        organization_id: str,
        created_by: Optional[str],
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        rag_enabled: bool = False,
        rag_vector_store_id: Optional[str] = None,
        rag_chunk_size: Optional[int] = None,
        rag_chunk_overlap: Optional[int] = None,
        rag_config: Optional[Dict[str, Any]] = None,
        rules: Optional[Dict[str, Any]] = None,
        default_model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> ResponseStatus:
        """Create a new project with RAG configuration."""
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                doc_repo = DocumentRepository(session)

                project = await repo.create_project(
                    name=name,
                    organization_id=organization_id,
                    created_by=created_by,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    rag_enabled=rag_enabled,
                    rag_vector_store_id=rag_vector_store_id,
                    rag_chunk_size=rag_chunk_size,
                    rag_chunk_overlap=rag_chunk_overlap,
                    rag_config=rag_config,
                    rules=rules,
                    default_model=default_model,
                    system_prompt=system_prompt,
                )

                payload = repo.serialize_project(project, include_relations=True)
                payload["documents"] = [
                    str(doc.id) for doc in await doc_repo.list_documents_by_project(str(project.id))
                ]
                return OK(message="Project created", data=payload)
        except Exception as exc:
            return InternalError(message=f"Failed to create project: {exc}")

    async def get_project(self, project_id: str, *, include_relations: bool = True) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                project = await repo.get_project(project_id, with_relations=include_relations)
                if not project:
                    return NotFound(message="Project not found", error_code="4004")

                payload = repo.serialize_project(project, include_relations=include_relations)
                if include_relations:
                    payload["documents"] = [
                        str(doc.id) for doc in await repo.get_project_documents(project_id)
                    ]
                return OK(data=payload)
        except Exception as exc:
            return InternalError(message=f"Failed to fetch project: {exc}")

    async def list_projects(
        self,
        *,
        organization_id: Optional[str] = None,
        limit: int = 100,
        include_relations: bool = False,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                projects = await repo.list_projects(
                    organization_id=organization_id,
                    limit=limit,
                    with_relations=include_relations,
                )
                data = [
                    repo.serialize_project(proj, include_relations=include_relations)
                    for proj in projects
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list projects: {exc}")

    async def update_project(
        self,
        project_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        rag_enabled: Optional[bool] = None,
        rag_vector_store_id: Optional[str] = None,
        rag_chunk_size: Optional[int] = None,
        rag_chunk_overlap: Optional[int] = None,
        rag_config: Optional[Dict[str, Any]] = None,
        rules: Optional[Dict[str, Any]] = None,
        default_model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                updated = await repo.update_project(
                    project_id,
                    name=name,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    rag_enabled=rag_enabled,
                    rag_vector_store_id=rag_vector_store_id,
                    rag_chunk_size=rag_chunk_size,
                    rag_chunk_overlap=rag_chunk_overlap,
                    rag_config=rag_config,
                    rules=rules,
                    default_model=default_model,
                    system_prompt=system_prompt,
                )
                if not updated:
                    return NotFound(message="Project not found", error_code="4004")
                return OK(message="Project updated", data=repo.serialize_project(updated))
        except Exception as exc:
            return InternalError(message=f"Failed to update project: {exc}")

    async def delete_project(self, project_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                deleted = await repo.delete_project(project_id)
                if not deleted:
                    return NotFound(message="Project not found", error_code="4004")
                return OK(message="Project deleted")
        except Exception as exc:
            return InternalError(message=f"Failed to delete project: {exc}")


project_service = ProjectService()
