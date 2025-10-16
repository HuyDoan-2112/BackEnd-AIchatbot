from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.core.response_status import ResponseStatus
from app.services.organization_service import organization_service

router = APIRouter()


def _send(result: ResponseStatus):
    if isinstance(result, ResponseStatus):
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    type: str = Field(default="company", pattern="^(country|company|department)$")
    description: Optional[str] = Field(default=None, max_length=500)
    parent_organization_id: Optional[str] = None
    country: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    rag_vector_store_id: Optional[str] = None
    rag_config: Optional[dict] = None


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    type: Optional[str] = Field(default=None, pattern="^(country|company|department)$")
    description: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    rag_vector_store_id: Optional[str] = None
    rag_config: Optional[dict] = None


class MembershipRequest(BaseModel):
    user_id: str
    role: Optional[str] = Field(default="member", pattern="^(owner|admin|member|viewer)$")


class RAGStoreUpdateRequest(BaseModel):
    rag_vector_store_id: str
    rag_config: Optional[dict] = None


@router.get("")
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: str = Depends(get_current_user)
):
    result = await organization_service.list_organizations(skip=skip, limit=limit)
    return _send(result)


@router.post("", status_code=201)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: str = Depends(get_current_user),
):
    result = await organization_service.create_organization(
        name=payload.name,
        type=payload.type,
        description=payload.description,
        parent_organization_id=payload.parent_organization_id,
        country=payload.country,
        location=payload.location,
        rag_vector_store_id=payload.rag_vector_store_id,
        rag_config=payload.rag_config,
    )
    return _send(result)


@router.get("/{organization_id}")
async def get_organization(
    organization_id: str,
    current_user: str = Depends(get_current_user)
):
    result = await organization_service.get_organization(organization_id)
    return _send(result)


@router.put("/{organization_id}")
async def update_organization(
    organization_id: str,
    payload: OrganizationUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    update_data = payload.dict(exclude_unset=True)
    result = await organization_service.update_organization(
        organization_id,
        **update_data
    )
    return _send(result)


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: str = Depends(get_current_user)
):
    result = await organization_service.delete_organization(organization_id)
    return _send(result)


@router.get("/{organization_id}/hierarchy")
async def get_hierarchy(
    organization_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get the full hierarchy path from root to this organization"""
    result = await organization_service.get_hierarchy(organization_id)
    return _send(result)


@router.get("/{organization_id}/children")
async def get_children(
    organization_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get direct children of this organization"""
    result = await organization_service.get_children(organization_id)
    return _send(result)


@router.get("/{organization_id}/members")
async def list_members(
    organization_id: str,
    current_user: str = Depends(get_current_user)
):
    result = await organization_service.list_members(organization_id)
    return _send(result)


@router.post("/{organization_id}/members", status_code=201)
async def add_member(
    organization_id: str,
    payload: MembershipRequest,
    current_user: str = Depends(get_current_user),
):
    result = await organization_service.add_member(
        organization_id,
        payload.user_id,
        payload.role or "member"
    )
    return _send(result)


@router.delete("/{organization_id}/members/{user_id}")
async def remove_member(
    organization_id: str,
    user_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await organization_service.remove_member(organization_id, user_id)
    return _send(result)


@router.put("/{organization_id}/rag-store")
async def update_rag_store(
    organization_id: str,
    payload: RAGStoreUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    """Update RAG vector store configuration for organization"""
    result = await organization_service.update_rag_store(
        organization_id,
        payload.rag_vector_store_id,
        payload.rag_config
    )
    return _send(result)
