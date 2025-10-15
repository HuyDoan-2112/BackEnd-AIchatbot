from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.core.response_status import ResponseStatus
from app.services import assistant_preset_service

router = APIRouter()


def _send(result: ResponseStatus):
    if isinstance(result, ResponseStatus):
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


class AssistantPresetCreateRequest(BaseModel):
    company_id: str
    name: str = Field(..., min_length=1, max_length=120)
    model_label: str = Field(..., min_length=1, max_length=120)
    project_id: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, max_length=5000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tools: Optional[Dict[str, Any]] = None


class AssistantPresetUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    system_prompt: Optional[str] = Field(default=None, max_length=5000)
    model_label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tools: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None


@router.get("/")
async def list_presets(
    company_id: str = Query(..., description="Company ID"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    include_usage: bool = Query(False, description="Include conversation usage references"),
    current_user: str = Depends(get_current_user),
):
    result = await assistant_preset_service.list_presets(
        company_id=company_id,
        project_id=project_id,
        include_usage=include_usage,
    )
    return _send(result)


@router.post("/", status_code=201)
async def create_preset(
    payload: AssistantPresetCreateRequest,
    current_user: str = Depends(get_current_user),
):
    result = await assistant_preset_service.create_preset(
        company_id=payload.company_id,
        name=payload.name,
        model_label=payload.model_label,
        project_id=payload.project_id,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature,
        top_p=payload.top_p,
        tools=payload.tools,
        created_by=current_user,
    )
    return _send(result)


@router.get("/{preset_id}")
async def get_preset(
    preset_id: str,
    include_usage: bool = Query(False),
    current_user: str = Depends(get_current_user),
):
    result = await assistant_preset_service.get_preset(preset_id, include_usage=include_usage)
    return _send(result)


@router.put("/{preset_id}")
async def update_preset(
    preset_id: str,
    payload: AssistantPresetUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    result = await assistant_preset_service.update_preset(
        preset_id,
        name=payload.name,
        system_prompt=payload.system_prompt,
        model_label=payload.model_label,
        temperature=payload.temperature,
        top_p=payload.top_p,
        tools=payload.tools,
        project_id=payload.project_id,
    )
    return _send(result)


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str, current_user: str = Depends(get_current_user)):
    result = await assistant_preset_service.delete_preset(preset_id)
    return _send(result)
