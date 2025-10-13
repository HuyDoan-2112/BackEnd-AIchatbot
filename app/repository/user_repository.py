import datetime
import time
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.postgresql import get_db_connection
from app.models.user_model import User
from app.core.response_status import *

class UserRepository:
    
    def __init__(self):
        self.db_connection = None
    
    def _get_db_connection(self):
        """Get database connection instance"""
        if self.db_connection is None:
            self.db_connection = get_db_connection()
        return self.db_connection

    async def create_user(self, username: str, email: str, hashed_password: str, refresh_token: str, refresh_token_expires_at: datetime) -> Dict[str, Any]:
        """Create a new user in the database"""
        try:
            async for session in self._get_db_connection().get_session():

                # Check if username or email already exists
                result = await session.execute(select(User).filter((User.username == username) | (User.email == email)))
                existing_user = result.scalar_one_or_none()
                if existing_user:
                    return BadRequest(message="Username or email already exists", error_code="4009")
                
                # Create new user with all fields
                from datetime import datetime as dt
                new_user = User(
                    username=username, 
                    email=email, 
                    hashed_password=hashed_password,
                    refresh_token=refresh_token,
                    refresh_token_expires_at=refresh_token_expires_at,
                    created_at=dt.utcnow().isoformat(),
                    is_active=True
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)

                return (
                    OK(message="User created successfully", data={
                        "id": new_user.id,
                        "username": new_user.username,
                        "email": new_user.email,
                        "created_at": new_user.created_at,
                    })
                )
        except Exception as e:
            return InternalError(message=f"Failed to create user: {str(e)}", error_code="5000")
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.username == username))
                user = result.scalar_one_or_none()
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "created_at": user.created_at,
                } if user else UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to get user by username: {str(e)}", error_code="5000")


    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "created_at": user.created_at,
                } if user else UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to get user by email: {str(e)}", error_code="5000")

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == user_id))
                user = result.scalar_one_or_none()
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at,
                } if user else UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to get user by id: {str(e)}", error_code="5000")
    
    async def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            async for session in self._get_db_connection().get_session():
                # Check if user exists
                result = await session.execute(select(User).filter(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    for key, value in data.items():
                        setattr(user, key, value)
                    await session.commit()
                    return OK(message="User updated successfully").send()
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to update user: {str(e)}", error_code="5000")

    async def delete_user(self, user_id: str) -> bool:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    await session.delete(user)
                    await session.commit()
                    return OK(message="User deleted successfully").send()
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to delete user: {str(e)}", error_code="5000")

    async def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.username == username))
                user = result.scalar_one_or_none()
                if user and user.verify_password(password):
                    return OK(message="Password is valid").send()
                return None
        except Exception as e:
            return InternalError(message=f"Failed to verify password: {str(e)}", error_code="5000")
    
    async def save_refresh_token(self, user_id: str, refresh_token: str, expires_at: int) -> bool:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.refresh_token = refresh_token
                    user.refresh_token_expires_at = expires_at
                    await session.commit()
                    return OK(message="Refresh token saved successfully").send()
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to save refresh token: {str(e)}", error_code="5000")

    async def verify_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.refresh_token == refresh_token))
                user = result.scalar_one_or_none()
                if user and user.refresh_token_expires_at and user.refresh_token_expires_at > int(time.time()):
                    return OK(message="Refresh token is valid", data={
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "created_at": user.created_at,
                    }).send()
                return NotFound(message="Invalid or expired refresh token", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to verify refresh token: {str(e)}", error_code="5000")

    async def invalidate_token(self, token: str) -> bool:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.refresh_token == token))
                user = result.scalar_one_or_none()
                if user:
                    user.refresh_token = None
                    user.refresh_token_expires_at = None
                    await session.commit()
                    return True
                return False
        except Exception as e:
            return InternalError(message=f"Failed to invalidate token: {str(e)}", error_code="5000")
