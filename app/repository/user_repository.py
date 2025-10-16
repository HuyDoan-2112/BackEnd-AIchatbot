import datetime
import time
from typing import Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.postgresql import get_db_connection
from app.models.user_model import User
from app.core.response_status import *
from app.core.logger import get_logger

logger = get_logger("user_repository")

class UserRepository:

    def __init__(self):
        self.db_connection = None
        logger.debug("UserRepository initialized")
    
    def _get_db_connection(self):
        """Get database connection instance"""
        if self.db_connection is None:
            self.db_connection = get_db_connection()
        return self.db_connection

    def _normalize_uuid(self, value: str, *, field: str) -> Union[str, ResponseStatus]:
        try:
            return str(UUID(str(value)))
        except Exception:
            return ValidationError(message=f"{field} must be a valid UUID", error_code="4002")

    def _serialize_user(self, user: User, *, include_sensitive: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        if include_sensitive:
            data["hashed_password"] = user.hashed_password
            data["refresh_token"] = user.refresh_token
            data["refresh_token_expires_at"] = user.refresh_token_expires_at
        return data

    async def create_user(self, username: str, email: str, hashed_password: str, refresh_token: str, refresh_token_expires_at: datetime) -> Dict[str, Any]:
        """Create a new user in the database"""
        logger.debug(f"Attempting to create user: {username} ({email})")
        try:
            async for session in self._get_db_connection().get_session():

                # Check if username or email already exists
                logger.debug(f"Checking if user already exists: {username} or {email}")
                result = await session.execute(select(User).filter((User.username == username) | (User.email == email)))
                existing_user = result.scalar_one_or_none()
                if existing_user:
                    logger.warning(f"User creation failed: Username or email already exists ({username}/{email})")
                    return BadRequest(message="Username or email already exists", error_code="4009")
                
                # Create new user with all fields
                logger.debug(f"Creating new user record: {username}")
                new_user = User(
                    username=username,
                    email=email,
                    hashed_password=hashed_password,
                    refresh_token=refresh_token,
                    refresh_token_expires_at=refresh_token_expires_at,
                    is_active=True
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)

                logger.info(f"User created successfully: {username} (ID: {new_user.id})")
                return (
                    OK(message="User created successfully", data={
                        "id": str(new_user.id),  # Convert UUID to string
                        "username": new_user.username,
                        "email": new_user.email,
                        "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
                    })
                )
        except Exception as e:
            logger.error(f"Failed to create user {username}: {str(e)}", exc_info=True)
            return InternalError(message=f"Failed to create user: {str(e)}", error_code="5000")
    
    async def get_user_by_username(self, username: str) -> Union[Dict[str, Any], ResponseStatus]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.username == username))
                user = result.scalar_one_or_none()
                if not user:
                    return UserNotFound(message="User not found", error_code="4004")
                return self._serialize_user(user, include_sensitive=True)
        except Exception as e:
            return InternalError(message=f"Failed to get user by username: {str(e)}", error_code="5000")


    async def get_user_by_email(self, email: str) -> Union[Dict[str, Any], ResponseStatus]:
        logger.debug(f"Looking up user by email: {email}")
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    logger.debug(f"User found: {user.username} ({email})")
                    return self._serialize_user(user, include_sensitive=True)
                else:
                    logger.debug(f"User not found: {email}")
                    return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {str(e)}", exc_info=True)
            return InternalError(message=f"Failed to get user by email: {str(e)}", error_code="5000")

    async def get_user_by_id(self, user_id: str) -> Union[Dict[str, Any], ResponseStatus]:
        normalized_id = self._normalize_uuid(user_id, field="user_id")
        if isinstance(normalized_id, ResponseStatus):
            return normalized_id

        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == normalized_id))
                user = result.scalar_one_or_none()
                if not user:
                    return UserNotFound(message="User not found", error_code="4004")
                return self._serialize_user(user)
        except Exception as e:
            return InternalError(message=f"Failed to get user by id: {str(e)}", error_code="5000")
    
    async def update_user(self, user_id: str, data: Dict[str, Any]) -> ResponseStatus:
        normalized_id = self._normalize_uuid(user_id, field="user_id")
        if isinstance(normalized_id, ResponseStatus):
            return normalized_id

        try:
            async for session in self._get_db_connection().get_session():
                # Check if user exists
                result = await session.execute(select(User).filter(User.id == normalized_id))
                user = result.scalar_one_or_none()
                if user:
                    for key, value in data.items():
                        setattr(user, key, value)
                    await session.commit()
                    await session.refresh(user)
                    return OK(
                        message="User updated successfully",
                        data=self._serialize_user(user)
                    )
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to update user: {str(e)}", error_code="5000")

    async def delete_user(self, user_id: str) -> ResponseStatus:
        normalized_id = self._normalize_uuid(user_id, field="user_id")
        if isinstance(normalized_id, ResponseStatus):
            return normalized_id

        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == normalized_id))
                user = result.scalar_one_or_none()
                if user:
                    await session.delete(user)
                    await session.commit()
                    return OK(message="User deleted successfully")
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to delete user: {str(e)}", error_code="5000")

    async def verify_password(self, username: str, password: str) -> Union[ResponseStatus, None, InternalError]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.username == username))
                user = result.scalar_one_or_none()
                if user and user.verify_password(password):
                    return OK(message="Password is valid")
                return None
        except Exception as e:
            return InternalError(message=f"Failed to verify password: {str(e)}", error_code="5000")
    
    async def save_refresh_token(self, user_id: str, refresh_token: str, expires_at: int) -> ResponseStatus:
        normalized_id = self._normalize_uuid(user_id, field="user_id")
        if isinstance(normalized_id, ResponseStatus):
            return normalized_id

        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.id == normalized_id))
                user = result.scalar_one_or_none()
                if user:
                    user.refresh_token = refresh_token
                    user.refresh_token_expires_at = expires_at
                    await session.commit()
                    return OK(message="Refresh token saved successfully")
                return UserNotFound(message="User not found", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to save refresh token: {str(e)}", error_code="5000")

    async def verify_refresh_token(self, refresh_token: str) -> ResponseStatus:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(User).filter(User.refresh_token == refresh_token))
                user = result.scalar_one_or_none()
                if user and user.refresh_token_expires_at and user.refresh_token_expires_at > int(time.time()):
                    return OK(
                        message="Refresh token is valid",
                        data=self._serialize_user(user)
                    )
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
