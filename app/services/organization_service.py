from typing import Optional, Dict, Any, List
from uuid import UUID

from app.db.postgresql import get_db_connection
from app.repository.organization_repository import OrganizationRepository
from app.core.response_status import ResponseStatus, OK, InternalError, NotFound, Conflict


class OrganizationService:
    """
    Service layer for organization operations, including hierarchy and membership management.
    """

    def __init__(self):
        self._db_connection = None

    def _get_db(self):
        if self._db_connection is None:
            self._db_connection = get_db_connection()
        return self._db_connection

    async def create_organization(
        self,
        *,
        name: str,
        type: str = "company",
        description: Optional[str] = None,
        parent_organization_id: Optional[str] = None,
        country: Optional[str] = None,
        location: Optional[str] = None,
        rag_vector_store_id: Optional[str] = None,
        rag_config: Optional[dict] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                
                # Check if parent exists
                if parent_organization_id:
                    parent = await repo.get_by_id(UUID(parent_organization_id))
                    if not parent:
                        return NotFound(message="Parent organization not found", error_code="4004")
                
                org = await repo.create(
                    name=name,
                    type=type,
                    description=description,
                    parent_organization_id=UUID(parent_organization_id) if parent_organization_id else None,
                    country=country,
                    location=location,
                    rag_vector_store_id=rag_vector_store_id,
                    rag_config=rag_config,
                )
                
                data = {
                    "id": str(org.id),
                    "name": org.name,
                    "type": org.type,
                    "description": org.description,
                    "parent_organization_id": str(org.parent_organization_id) if org.parent_organization_id else None,
                    "country": org.country,
                    "location": org.location,
                    "rag_vector_store_id": org.rag_vector_store_id,
                    "created_at": org.created_at,
                }
                return OK(message="Organization created", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to create organization: {exc}")

    async def get_organization(self, organization_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                org = await repo.get_by_id(UUID(organization_id))
                if not org:
                    return NotFound(message="Organization not found", error_code="4004")
                
                data = {
                    "id": str(org.id),
                    "name": org.name,
                    "type": org.type,
                    "description": org.description,
                    "parent_organization_id": str(org.parent_organization_id) if org.parent_organization_id else None,
                    "country": org.country,
                    "location": org.location,
                    "rag_vector_store_id": org.rag_vector_store_id,
                    "rag_config": org.rag_config,
                    "created_at": org.created_at,
                    "updated_at": org.updated_at,
                }
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to fetch organization: {exc}")

    async def list_organizations(self, skip: int = 0, limit: int = 100) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                organizations = await repo.get_all(skip=skip, limit=limit)
                
                data = [
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "type": org.type,
                        "description": org.description,
                        "parent_organization_id": str(org.parent_organization_id) if org.parent_organization_id else None,
                        "country": org.country,
                        "location": org.location,
                    }
                    for org in organizations
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list organizations: {exc}")

    async def update_organization(
        self,
        organization_id: str,
        **kwargs
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                updated = await repo.update(UUID(organization_id), **kwargs)
                if not updated:
                    return NotFound(message="Organization not found", error_code="4004")
                
                data = {
                    "id": str(updated.id),
                    "name": updated.name,
                    "type": updated.type,
                    "description": updated.description,
                    "parent_organization_id": str(updated.parent_organization_id) if updated.parent_organization_id else None,
                    "country": updated.country,
                    "location": updated.location,
                    "rag_vector_store_id": updated.rag_vector_store_id,
                    "updated_at": updated.updated_at,
                }
                return OK(message="Organization updated", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to update organization: {exc}")

    async def delete_organization(self, organization_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                success = await repo.delete(UUID(organization_id))
                if not success:
                    return NotFound(message="Organization not found", error_code="4004")
                return OK(message="Organization deleted")
        except Exception as exc:
            return InternalError(message=f"Failed to delete organization: {exc}")

    async def get_hierarchy(self, organization_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                hierarchy = await repo.get_hierarchy(UUID(organization_id))
                
                data = [
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "type": org.type,
                        "level": idx,
                    }
                    for idx, org in enumerate(hierarchy)
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to get hierarchy: {exc}")

    async def get_children(self, organization_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                children = await repo.get_children(UUID(organization_id))
                
                data = [
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "type": org.type,
                        "description": org.description,
                    }
                    for org in children
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to get children: {exc}")

    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member"
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                membership = await repo.add_member(
                    UUID(organization_id),
                    UUID(user_id),
                    role
                )
                
                data = {
                    "organization_id": str(membership.organization_id),
                    "user_id": str(membership.user_id),
                    "role": membership.role,
                    "joined_at": membership.joined_at,
                }
                return OK(message="Member added", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to add member: {exc}")

    async def remove_member(
        self,
        organization_id: str,
        user_id: str
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                success = await repo.remove_member(UUID(organization_id), UUID(user_id))
                if not success:
                    return NotFound(message="Membership not found", error_code="4004")
                return OK(message="Member removed")
        except Exception as exc:
            return InternalError(message=f"Failed to remove member: {exc}")

    async def list_members(self, organization_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                members = await repo.get_members(UUID(organization_id))
                
                data = [
                    {
                        "user_id": str(m.user_id),
                        "role": m.role,
                        "joined_at": m.joined_at,
                    }
                    for m in members
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list members: {exc}")

    async def update_rag_store(
        self,
        organization_id: str,
        rag_vector_store_id: str,
        rag_config: Optional[dict] = None
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = OrganizationRepository(session)
                updated = await repo.update_rag_store(
                    UUID(organization_id),
                    rag_vector_store_id,
                    rag_config
                )
                if not updated:
                    return NotFound(message="Organization not found", error_code="4004")
                
                data = {
                    "id": str(updated.id),
                    "name": updated.name,
                    "rag_vector_store_id": updated.rag_vector_store_id,
                    "rag_config": updated.rag_config,
                }
                return OK(message="RAG store updated", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to update RAG store: {exc}")


organization_service = OrganizationService()
