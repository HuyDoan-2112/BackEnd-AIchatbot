from typing import Dict, Any

from app.repository.user_repository import UserRepository
from app.core.response_status import ResponseStatus, OK, InternalError


class UserService:
    def __init__(self) -> None:
        self._repo = UserRepository()

    async def get_user(self, user_id: str) -> ResponseStatus:
        try:
            result = await self._repo.get_user_by_id(user_id)
            if isinstance(result, ResponseStatus):
                return result
            return OK(message="User fetched", data=result)
        except Exception as exc:
            return InternalError(message=f"Failed to fetch user: {exc}")

    async def update_user(self, user_id: str, payload: Dict[str, Any]) -> ResponseStatus:
        try:
            result = await self._repo.update_user(user_id, payload)
            if isinstance(result, ResponseStatus):
                return result
            return OK(message="User updated", data=result)
        except Exception as exc:
            return InternalError(message=f"Failed to update user: {exc}")


user_service = UserService()
