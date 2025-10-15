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


@router.get("/")
async def list_projects(
    company_id: Optional[str] = Query(None, description="Filter projects by company ID"),
    limit: int = Query(100, ge=1, le=500),
    include_relations: bool = Query(True, description="Include linked conversations/documents"),
    current_user: str = Depends(get_current_user),
):
    result = await project_service.list_projects(
    company_id=company_id,
    limit=limit,
    include_relations=include_relations,
    )
    return _send(result)


@router.post("/", status_code=201)
async def create_project(
    request: ProjectRequest,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.create_project(
        name=request.name,
        company_id=str(request.company_id),
        created_by=current_user,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        conversation_ids=[str(cid) for cid in request.conversation_ids],
        document_ids=[str(did) for did in request.document_ids],
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
    result = await project_service.update_project(
        project_id,
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return _send(result)


@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user: str = Depends(get_current_user)):
    result = await project_service.delete_project(project_id)
    return _send(result)


@router.get("/{project_id}/conversations")
async def list_project_conversations(project_id: str, current_user: str = Depends(get_current_user)):
    result = await project_service.get_project(project_id, include_relations=True)
    if isinstance(result, ResponseStatus):
        if result.success and result.data:
            payload = {
                "project_id": project_id,
                "conversation_ids": result.data.get("conversation_ids", []),
            }
            return OK(data=payload).send()
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


@router.post("/{project_id}/conversations/{conversation_id}", status_code=201)
async def attach_conversation(
    project_id: str,
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.attach_conversation(project_id, conversation_id)
    return _send(result)


@router.delete("/{project_id}/conversations/{conversation_id}")
async def detach_conversation(
    project_id: str,
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.detach_conversation(project_id, conversation_id)
    return _send(result)


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str, current_user: str = Depends(get_current_user)):
    result = await project_service.get_project(project_id, include_relations=True)
    if isinstance(result, ResponseStatus):
        if result.success and result.data:
            payload = {
                "project_id": project_id,
                "document_ids": result.data.get("documents", []),
            }
            return OK(data=payload).send()
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


@router.post("/{project_id}/documents/{document_id}", status_code=201)
async def attach_document(
    project_id: str,
    document_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.attach_document(project_id, document_id)
    return _send(result)


@router.delete("/{project_id}/documents/{document_id}")
async def detach_document(
    project_id: str,
    document_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await project_service.detach_document(project_id, document_id)
    return _send(result)
