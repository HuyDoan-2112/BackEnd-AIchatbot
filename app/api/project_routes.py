from typing import Optional

from fastapi import APIRouter, Depends, Query, Body, HTTPException

from app.core.dependencies import get_current_user
from app.core.response_status import ResponseStatus, OK
from app.schemas import ProjectRequest, ProjectUpdateRequest
from app.services import project_service

router = APIRouter()


def _send(result: ResponseStatus):
    if isinstance(result, ResponseStatus):
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


@router.get("")
async def list_projects(
    organization_id: Optional[str] = Query(None, description="Filter projects by organization ID"),
    limit: int = Query(100, ge=1, le=500),
    include_relations: bool = Query(True, description="Include linked conversations/documents"),
    current_user: str = Depends(get_current_user),
):
    result = await project_service.list_projects(
        organization_id=organization_id,
        limit=limit,
        include_relations=include_relations,
    )
    return _send(result)


@router.post("", status_code=201)
async def create_project(
    request: ProjectRequest,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.create_project(
        name=request.name,
        organization_id=str(request.organization_id),
        created_by=current_user,
        description=request.description,
        rag_enabled=request.rag_enabled,
        rag_vector_store_id=request.rag_vector_store_id,
        rag_chunk_size=request.rag_chunk_size,
        rag_chunk_overlap=request.rag_chunk_overlap,
        rag_config=request.rag_config,
        rules=request.rules,
        default_model=request.default_model,
        system_prompt=request.system_prompt,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    return _send(result)


@router.get("/{project_id}")
async def get_project(project_id: str, current_user: str = Depends(get_current_user)):
    result = await project_service.get_project(project_id, include_relations=True)
    return _send(result)


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest = Body(...),
    current_user: str = Depends(get_current_user),
):
    update_data = payload.dict(exclude_unset=True)
    result = await project_service.update_project(project_id, **update_data)
    return _send(result)


@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user: str = Depends(get_current_user)):
    result = await project_service.delete_project(project_id)
    return _send(result)


@router.get("/{project_id}/conversations")
async def list_project_conversations(project_id: str, current_user: str = Depends(get_current_user)):
    """Get all conversations for a project (direct relationship)"""
    result = await project_service.get_project_conversations(project_id)
    return _send(result)


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str, current_user: str = Depends(get_current_user)):
    """Get all documents for a project (direct relationship)"""
    result = await project_service.get_project_documents(project_id)
    return _send(result)
