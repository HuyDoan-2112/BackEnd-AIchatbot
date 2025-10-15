from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.postgresql import get_db_connection
from app.repository.project_repository import ProjectRepository
from app.repository.link_repository import LinkRepository
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
        company_id: str,
        created_by: Optional[str],
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        conversation_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                link_repo = LinkRepository(session)
                doc_repo = DocumentRepository(session)

                project = await repo.create_project(
                    name=name,
                    company_id=company_id,
                    created_by=created_by,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Link existing conversations/documents if provided
                if conversation_ids:
                    for conv_id in conversation_ids:
                        await link_repo.link_chat_to_project(str(project.id), conv_id)

                if document_ids:
                    for doc_id in document_ids:
                        await link_repo.link_document_to_project(str(project.id), doc_id)

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
        company_id: Optional[str] = None,
        limit: int = 100,
        include_relations: bool = False,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = ProjectRepository(session)
                projects = await repo.list_projects(
                    company_id=company_id,
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

    async def attach_conversation(self, project_id: str, conversation_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                link_repo = LinkRepository(session)
                link = await link_repo.link_chat_to_project(project_id, conversation_id)
                if isinstance(link, ResponseStatus):
                    return link
                return OK(message="Conversation linked", data={"project_id": project_id, "conversation_id": conversation_id})
        except Exception as exc:
            return InternalError(message=f"Failed to link conversation: {exc}")

    async def detach_conversation(self, project_id: str, conversation_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                link_repo = LinkRepository(session)
                removed = await link_repo.unlink_chat_from_project(project_id, conversation_id)
                if not removed:
                    return NotFound(message="Link not found", error_code="4004")
                return OK(message="Conversation unlinked")
        except Exception as exc:
            return InternalError(message=f"Failed to unlink conversation: {exc}")

    async def attach_document(self, project_id: str, document_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                link_repo = LinkRepository(session)
                link = await link_repo.link_document_to_project(project_id, document_id)
                if isinstance(link, ResponseStatus):
                    return link
                return OK(message="Document linked", data={"project_id": project_id, "document_id": document_id})
        except Exception as exc:
            return InternalError(message=f"Failed to link document: {exc}")

    async def detach_document(self, project_id: str, document_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                link_repo = LinkRepository(session)
                removed = await link_repo.unlink_document_from_project(project_id, document_id)
                if not removed:
                    return NotFound(message="Link not found", error_code="4004")
                return OK(message="Document unlinked")
        except Exception as exc:
            return InternalError(message=f"Failed to unlink document: {exc}")


project_service = ProjectService()
