from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.core.response_status import ResponseStatus
from app.services import company_service

router = APIRouter()


def _send(result: ResponseStatus):
    if isinstance(result, ResponseStatus):
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


class CompanyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=200)


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=200)


class MembershipRequest(BaseModel):
    user_id: str
    role: Optional[str] = "member"


@router.get("/")
async def list_companies(current_user: str = Depends(get_current_user)):
    result = await company_service.list_companies()
    return _send(result)


@router.post("/", status_code=201)
async def create_company(
    payload: CompanyCreateRequest,
    current_user: str = Depends(get_current_user),
):
    result = await company_service.create_company(
        name=payload.name,
        description=payload.description,
        location=payload.location,
    )
    return _send(result)


@router.get("/{company_id}")
async def get_company(company_id: str, current_user: str = Depends(get_current_user)):
    result = await company_service.get_company(company_id)
    return _send(result)


@router.put("/{company_id}")
async def update_company(
    company_id: str,
    payload: CompanyUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    result = await company_service.update_company(
        company_id,
        name=payload.name,
        description=payload.description,
        location=payload.location,
    )
    return _send(result)


@router.delete("/{company_id}")
async def delete_company(company_id: str, current_user: str = Depends(get_current_user)):
    result = await company_service.delete_company(company_id)
    return _send(result)


@router.get("/{company_id}/members")
async def list_members(company_id: str, current_user: str = Depends(get_current_user)):
    result = await company_service.list_members(company_id)
    return _send(result)


@router.post("/{company_id}/members", status_code=201)
async def add_member(
    company_id: str,
    payload: MembershipRequest,
    current_user: str = Depends(get_current_user),
):
    result = await company_service.add_member(company_id, payload.user_id, payload.role or "member")
    return _send(result)


@router.delete("/{company_id}/members/{user_id}")
async def remove_member(
    company_id: str,
    user_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await company_service.remove_member(company_id, user_id)
    return _send(result)
