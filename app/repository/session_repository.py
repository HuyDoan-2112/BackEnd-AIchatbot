import datetime
import time
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.postgresql import get_db_connection
from app.core.response_status import *
from app.models.auth_model import AuthSession

class SessionRepository:
    
    def __init__(self):
        self.db_connection = None
    
    def _get_db_connection(self):
        """Get database connection instance"""
        if self.db_connection is None:
            self.db_connection = get_db_connection()
        return self.db_connection
    
    async def create_session(self, user_id: str, refresh_token: str, refresh_token_expires_at: datetime) -> Dict[str, Any]:
        """Create a new session in the database"""
        try:
            async for session in self._get_db_connection().get_session():
                new_session = AuthSession(
                    user_id=user_id,
                    refresh_token=refresh_token,
                    expires_at=refresh_token_expires_at
                )
                session.add(new_session)
                await session.commit()
                await session.refresh(new_session)
                return OK(message="Session created successfully", data={
                    "id": new_session.id,
                    "user_id": new_session.user_id,
                    "refresh_token": new_session.refresh_token,
                    "refresh_token_expires_at": new_session.refresh_token_expires_at,
                    "created_at": new_session.created_at,
                }
            )
        except Exception as e:
            return InternalError(message=f"Failed to create session: {str(e)}", error_code="5000")
    async def get_session_by_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(AuthSession).filter(AuthSession.refresh_token == refresh_token))
                auth_session = result.scalar_one_or_none()
                return {
                    "id": auth_session.id,
                    "user_id": auth_session.user_id,
                    "refresh_token": auth_session.refresh_token,
                    "expires_at": auth_session.expires_at,
                    "created_at": auth_session.created_at,
                    "revoked": auth_session.revoked
                } if auth_session else None
        except Exception as e:
            return InternalError(message=f"Failed to get session by refresh token: {str(e)}", error_code="5000")
            
            
    async def revoke_session(self, refresh_token: str) -> bool:
        """Revoke a session by its refresh token"""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(AuthSession).filter(AuthSession.refresh_token == refresh_token))
                auth_session = result.scalar_one_or_none()
                if auth_session:
                    auth_session.revoked = True
                    await session.commit()
                    return True
                return False
        except Exception as e:
            return InternalError(message=f"Failed to revoke session: {str(e)}", error_code="5000")
        
    async def revoke_sessions_by_user_id(self, user_id: str) -> int:
        """Revoke all sessions for a given user ID"""
        try:
            async for session in self._get_db_connection().get_session():
                result = await session.execute(select(AuthSession).filter(AuthSession.user_id == user_id, AuthSession.revoked == False))
                auth_sessions = result.scalars().all()
                count = 0
                for auth_session in auth_sessions:
                    auth_session.revoked = True
                    count += 1
                await session.commit()
                return count
        except Exception as e:
            return InternalError(message=f"Failed to revoke sessions by user id: {str(e)}", error_code="5000")
        
    async def delete_expired_sessions(self) -> int:
        """Delete all expired sessions"""
        try:
            async for session in self._get_db_connection().get_session():
                current_time = datetime.datetime.utcnow()
                result = await session.execute(select(AuthSession).filter(AuthSession.expires_at < current_time))
                expired_sessions = result.scalars().all()
                count = 0
                for auth_session in expired_sessions:
                    await session.delete(auth_session)
                    count += 1
                await session.commit()
                return count
        except Exception as e:
            return InternalError(message=f"Failed to delete expired sessions: {str(e)}", error_code="5000")
        
    
