from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.schemas import ProjectRequest
import uuid
from app.services import project_service

router = APIRouter()



@router.get("/")
def read_projects(current_user: str = Depends(get_current_user)):
    return [{"project_id": 1, "name": "Project 1"}, {"project_id": 2, "name": "Project 2"}]


@router.post("/")
def create_project(name: str, request: ProjectRequest, current_user: str = Depends(get_current_user)):
    new_project = {"project_id": 3, "name": request.name}
    return new_project

@router.delete("/{project_id}")
def delete_project(project_id: int, current_user: str = Depends(get_current_user)):
    return {"message": f"Project {project_id} deleted"}

@router.put("/{project_id}")
def update_project(project_id: int, conversation_id: uuid.UUID, name: str, current_user: str = Depends(get_current_user)):
    updated_project = {"project_id": project_id, "name": name}
    return updated_project

@router.put("/{project_id}/")
def archive_project(project_id: int, current_user: str = Depends(get_current_user)):
    return {"message": f"Project {project_id} archived"}

@router.get("/{project_id}/chat")
def get_chat(project_id: int, current_user: str = Depends(get_current_user)):
    return [{"conversation_id": 1, "title": "Conversation 1"}, {"conversation_id": 2, "title": "Conversation 2"}]