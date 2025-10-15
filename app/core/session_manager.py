"""
Session management for anonymous and authenticated users.
Handles session creation, validation, and tracking.
"""
import uuid
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from app.core.logger import get_logger

logger = get_logger("session_manager")


@dataclass
class UserSession:
    """User session data"""
    session_id: str
    is_authenticated: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    created_at: float = None
    expires_at: float = None
    request_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.expires_at is None:
            # Anonymous sessions expire after 24 hours
            if not self.is_authenticated:
                self.expires_at = time.time() + (24 * 60 * 60)
            else:
                # Authenticated sessions don't expire (managed by JWT)
                self.expires_at = time.time() + (365 * 24 * 60 * 60)

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return time.time() > self.expires_at

    def increment_request_count(self):
        """Increment request counter"""
        self.request_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "is_authenticated": self.is_authenticated,
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "request_count": self.request_count
        }


class SessionManager:
    """Manages user sessions (both anonymous and authenticated)"""

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}
        logger.info("SessionManager initialized")

    def create_anonymous_session(self) -> UserSession:
        """Create a new anonymous session"""
        session_id = f"anon_{uuid.uuid4().hex}"
        session = UserSession(
            session_id=session_id,
            is_authenticated=False
        )
        self._sessions[session_id] = session
        logger.info(f"Created anonymous session: {session_id}")
        return session

    def create_authenticated_session(self, user_id: str, username: str, email: str) -> UserSession:
        """Create a new authenticated session"""
        session_id = f"auth_{uuid.uuid4().hex}"
        session = UserSession(
            session_id=session_id,
            is_authenticated=True,
            user_id=user_id,
            username=username,
            email=email
        )
        self._sessions[session_id] = session
        logger.info(f"Created authenticated session for user: {username} (ID: {session_id})")
        return session

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            logger.debug(f"Session expired: {session_id}")
            self.remove_session(session_id)
            return None
        return session

    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Removed session: {session_id}")

    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if session.is_expired()
        ]
        for sid in expired_sessions:
            self.remove_session(sid)
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def get_session_count(self) -> Dict[str, int]:
        """Get session statistics"""
        authenticated = sum(1 for s in self._sessions.values() if s.is_authenticated)
        anonymous = sum(1 for s in self._sessions.values() if not s.is_authenticated)
        return {
            "total": len(self._sessions),
            "authenticated": authenticated,
            "anonymous": anonymous
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
