from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.company_model import Company
from app.models.company_membership_model import CompanyMembership


class CompanyRepository:
    """
    Repository for managing Company CRUD operations and data access.
    Used to handle organization-level queries and validations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------
    # ✅ CREATE
    # ------------------------------------------------------------
    async def create_company(
        self, name: str, description: Optional[str] = None, location: Optional[str] = None
    ) -> Company:
        """
        Create and persist a new company.
        """
        company = Company(name=name, description=description, location=location)
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        return company

    # ------------------------------------------------------------
    # ✅ READ
    # ------------------------------------------------------------
    async def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """
        Retrieve a company by its ID.
        Loads relationships (users, projects, etc.) if needed.
        """
        result = await self.db.execute(
            select(Company)
            .where(Company.id == company_id)
            .options(
                selectinload(Company.projects),
                selectinload(Company.documents),
                selectinload(Company.conversations),
                selectinload(Company.users),
                selectinload(Company.memberships),
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, company_id: str) -> List[CompanyMembership]:
        """
        List all memberships for a company.
        """
        result = await self.db.execute(
            select(CompanyMembership).where(CompanyMembership.company_id == company_id)
        )
        return result.scalars().all()

    async def add_member(self, company_id: str, user_id: str, role: str = "member") -> CompanyMembership:
        """
        Add or update a member within the company.
        """
        membership = await self.db.get(CompanyMembership, (company_id, user_id))
        if membership:
            membership.role = role
        else:
            membership = CompanyMembership(company_id=company_id, user_id=user_id, role=role)
            self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_member(self, company_id: str, user_id: str) -> bool:
        """
        Remove a member from the company.
        """
        membership = await self.db.get(CompanyMembership, (company_id, user_id))
        if not membership:
            return False
        await self.db.delete(membership)
        await self.db.commit()
        return True

    async def get_company_by_name(self, name: str) -> Optional[Company]:
        """
        Retrieve a company by its name.
        """
        result = await self.db.execute(select(Company).where(Company.name == name))
        return result.scalar_one_or_none()

    async def list_all_companies(self) -> List[Company]:
        """
        Return all registered companies (for admin use).
        """
        result = await self.db.execute(select(Company))
        return result.scalars().all()

    # ------------------------------------------------------------
    # ✅ UPDATE
    # ------------------------------------------------------------
    async def update_company_info(
        self,
        company_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Optional[Company]:
        """
        Update the basic information of a company.
        Only provided fields will be updated.
        """
        values = {}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if location is not None:
            values["location"] = location

        if not values:
            return None  # nothing to update

        stmt = (
            update(Company)
            .where(Company.id == company_id)
            .values(**values)
            .returning(Company)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    # ------------------------------------------------------------
    # ✅ DELETE
    # ------------------------------------------------------------
    async def delete_company(self, company_id: str) -> bool:
        """
        Permanently delete a company and all its relationships (cascades).
        Be careful with this in production.
        """
        stmt = delete(Company).where(Company.id == company_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------
    # ✅ VALIDATION / HELPERS
    # ------------------------------------------------------------
    async def is_company_exist(self, name: str) -> bool:
        """
        Check if a company with this name already exists.
        """
        result = await self.db.execute(select(Company).where(Company.name == name))
        return result.scalar_one_or_none() is not None

    async def verify_company_access(self, company_id: str, user_id: str) -> bool:
        """
        Verify that a user belongs to the same company before accessing its resources.
        """
        result = await self.db.execute(
            select(Company)
            .join(Company.memberships)
            .where(
                Company.id == company_id,
                CompanyMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None
