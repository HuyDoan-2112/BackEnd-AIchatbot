from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.core.response_status import ResponseStatus
from app.services import user_service

router = APIRouter()


def _send(result: ResponseStatus):
    if isinstance(result, ResponseStatus):
        return result.send()
    raise HTTPException(status_code=500, detail="Unexpected service response")


@router.get("/{user_id}")
async def get_user(user_id: str, current_user: str = Depends(get_current_user)):
    result = await user_service.get_user(user_id)
    return _send(result)


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    payload: Dict[str, Any],
    current_user: str = Depends(get_current_user),
):
    result = await user_service.update_user(user_id, payload)
    return _send(result)
