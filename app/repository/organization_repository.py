"""
Repository for Organization CRUD operations and hierarchy management.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_model import Organization
from app.models.organization_membership_model import OrganizationMembership


class OrganizationRepository:
    """Repository for managing organizations and hierarchical structures."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        type: str = "company",
        description: Optional[str] = None,
        parent_organization_id: Optional[UUID] = None,
        country: Optional[str] = None,
        location: Optional[str] = None,
        rag_vector_store_id: Optional[str] = None,
        rag_config: Optional[dict] = None,
    ) -> Organization:
        """Create a new organization."""
        organization = Organization(
            name=name,
            type=type,
            description=description,
            parent_organization_id=parent_organization_id,
            country=country,
            location=location,
            rag_vector_store_id=rag_vector_store_id,
            rag_config=rag_config,
        )
        self.db.add(organization)
        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        """Get organization by ID."""
        return await self.db.get(Organization, organization_id)

    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name."""
        stmt = select(Organization).where(Organization.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        """Get all organizations with pagination."""
        stmt = select(Organization).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_children(self, parent_id: UUID) -> List[Organization]:
        """Get all direct children of an organization."""
        stmt = select(Organization).where(Organization.parent_organization_id == parent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_hierarchy(self, organization_id: UUID) -> List[Organization]:
        """
        Get the full hierarchy path from root to this organization.
        Returns list from root → ... → current organization.
        """
        hierarchy: List[Organization] = []
        current = await self.get_by_id(organization_id)

        while current:
            hierarchy.insert(0, current)
            if current.parent_organization_id:
                current = await self.get_by_id(current.parent_organization_id)
            else:
                break

        return hierarchy

    async def get_all_descendants(self, organization_id: UUID) -> List[Organization]:
        """Get all descendants recursively (children, grandchildren, etc.)."""
        descendants: List[Organization] = []
        children = await self.get_children(organization_id)

        for child in children:
            descendants.append(child)
            descendants.extend(await self.get_all_descendants(child.id))

        return descendants

    async def update(self, organization_id: UUID, **kwargs) -> Optional[Organization]:
        """Update organization fields."""
        organization = await self.get_by_id(organization_id)
        if not organization:
            return None

        for key, value in kwargs.items():
            if hasattr(organization, key):
                setattr(organization, key, value)

        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def delete(self, organization_id: UUID) -> bool:
        """Delete an organization (cascades to children)."""
        organization = await self.get_by_id(organization_id)
        if not organization:
            return False

        await self.db.delete(organization)
        await self.db.commit()
        return True

    async def add_member(
        self,
        organization_id: UUID,
        user_id: UUID,
        role: str = "member"
    ) -> OrganizationMembership:
        """Add a user to an organization."""
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_member(self, organization_id: UUID, user_id: UUID) -> bool:
        """Remove a user from an organization."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        ).limit(1)
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership:
            return False

        await self.db.delete(membership)
        await self.db.commit()
        return True

    async def get_members(self, organization_id: UUID) -> List[OrganizationMembership]:
        """Get all members of an organization."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_rag_store(
        self,
        organization_id: UUID,
        rag_vector_store_id: str,
        rag_config: Optional[dict] = None
    ) -> Optional[Organization]:
        """Update RAG vector store configuration for an organization."""
        return await self.update(
            organization_id,
            rag_vector_store_id=rag_vector_store_id,
            rag_config=rag_config
        )
