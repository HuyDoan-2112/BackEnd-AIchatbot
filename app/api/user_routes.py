from typing import Any, Dict
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/{user_id}")
def get_user(user_id: str, current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    return {"user_id": user_id, "requested_by": current_user}

@router.put("/{user_id}")
def update_user(user_id: str, payload: Dict[str, Any], current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    return {"user_id": user_id, "payload": payload, "updated_by": current_user}
