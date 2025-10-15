from typing import Optional, Dict, Any, List

from app.db.postgresql import get_db_connection
from app.repository.company_repository import CompanyRepository
from app.core.response_status import ResponseStatus, OK, InternalError, NotFound, Conflict


class CompanyService:
    """
    Service layer for company operations, including membership management.
    """

    def __init__(self):
        self._db_connection = None

    def _get_db(self):
        if self._db_connection is None:
            self._db_connection = get_db_connection()
        return self._db_connection

    async def create_company(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                if await repo.is_company_exist(name):
                    return Conflict(message="Company name already exists", error_code="4009")
                company = await repo.create_company(name, description, location)
                data = {
                    "id": str(company.id),
                    "name": company.name,
                    "description": company.description,
                    "location": company.location,
                }
                return OK(message="Company created", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to create company: {exc}")

    async def get_company(self, company_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                company = await repo.get_company_by_id(company_id)
                if not company:
                    return NotFound(message="Company not found", error_code="4004")
                data = {
                    "id": str(company.id),
                    "name": company.name,
                    "description": company.description,
                    "location": company.location,
                }
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to fetch company: {exc}")

    async def list_companies(self) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                companies = await repo.list_all_companies()
                data = [
                    {
                        "id": str(company.id),
                        "name": company.name,
                        "description": company.description,
                        "location": company.location,
                    }
                    for company in companies
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list companies: {exc}")

    async def update_company(
        self,
        company_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                updated = await repo.update_company_info(company_id, name, description, location)
                if not updated:
                    return NotFound(message="Company not found or no changes", error_code="4004")
                data = {
                    "id": str(updated.id),
                    "name": updated.name,
                    "description": updated.description,
                    "location": updated.location,
                }
                return OK(message="Company updated", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to update company: {exc}")

    async def delete_company(self, company_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                removed = await repo.delete_company(company_id)
                if not removed:
                    return NotFound(message="Company not found", error_code="4004")
                return OK(message="Company deleted")
        except Exception as exc:
            return InternalError(message=f"Failed to delete company: {exc}")

    async def list_members(self, company_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                members = await repo.list_members(company_id)
                data = [
                    {
                        "company_id": str(member.company_id),
                        "user_id": str(member.user_id),
                        "role": member.role,
                        "joined_at": member.joined_at,
                    }
                    for member in members
                ]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list company members: {exc}")

    async def add_member(self, company_id: str, user_id: str, role: str = "member") -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                membership = await repo.add_member(company_id, user_id, role)
                data = {
                    "company_id": str(membership.company_id),
                    "user_id": str(membership.user_id),
                    "role": membership.role,
                    "joined_at": membership.joined_at,
                }
                return OK(message="Member added", data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to add member: {exc}")

    async def remove_member(self, company_id: str, user_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = CompanyRepository(session)
                removed = await repo.remove_member(company_id, user_id)
                if not removed:
                    return NotFound(message="Membership not found", error_code="4004")
                return OK(message="Member removed")
        except Exception as exc:
            return InternalError(message=f"Failed to remove member: {exc}")


company_service = CompanyService()
