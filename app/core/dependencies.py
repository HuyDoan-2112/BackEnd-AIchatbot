"""
Authentication dependencies for protected routes.
"""
from fastapi import Header, HTTPException, Depends, Request
from typing import Optional
from app.core.jwt import decode_token
from app.core.response_status import TokenExpired, InvalidToken
from app.core.model_registry import get_model_registry, ModelRegistry
from app.core.config import get_settings, Settings
from app.core.session_manager import get_session_manager, UserSession
from app.core.logger import get_logger

logger = get_logger("dependencies")


async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Dependency to get the current authenticated user from JWT token.

    Usage:
        @router.get("/protected")
        async def protected_route(user_id: str = Depends(get_current_user)):
            return {"user_id": user_id}
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        payload = decode_token(token)

        # Check if decode returned an error response
        if isinstance(payload, TokenExpired):
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if isinstance(payload, InvalidToken):
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Dependency to optionally get the current user from JWT token.
    Returns None if no valid token is provided instead of raising an exception.

    Usage:
        @router.get("/maybe-protected")
        async def route(user_id: Optional[str] = Depends(get_optional_user)):
            if user_id:
                return {"message": "Authenticated", "user_id": user_id}
            return {"message": "Anonymous"}
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


async def get_current_user_or_anonymous(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Dependency to get current user (authenticated or anonymous).
    Creates anonymous session if no authentication provided.

    Returns dict with:
    - is_authenticated: bool
    - user_id: Optional[str]
    - session_id: str
    - request_count: int
    """
    session_manager = get_session_manager()

    # Check if session already set by middleware
    if hasattr(request.state, "session"):
        return request.state.session.to_dict()

    # Try to authenticate with JWT
    if authorization:
        try:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                payload = decode_token(token)

                if not isinstance(payload, (TokenExpired, InvalidToken)):
                    user_id = payload.get("sub")
                    if user_id:
                        logger.debug(f"Authenticated user: {user_id}")
                        session = session_manager.create_authenticated_session(
                            user_id=user_id,
                            username="",
                            email=""
                        )
                        request.state.session = session
                        return session.to_dict()
        except Exception as e:
            logger.debug(f"Authentication failed, using anonymous: {e}")

    # Check for existing anonymous session cookie
    session_id = request.cookies.get("session_id")
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            logger.debug(f"Using existing session: {session_id}")
            request.state.session = session
            return session.to_dict()

    # Create new anonymous session
    logger.info("Creating new anonymous session")
    session = session_manager.create_anonymous_session()
    request.state.session = session
    return session.to_dict()


def require_authentication(user: dict = Depends(get_current_user_or_anonymous)):
    """
    Dependency that requires user to be authenticated.
    Raises 403 if anonymous user tries to access.
    """
    if not user.get("is_authenticated"):
        logger.warning("Anonymous user attempted to access authenticated-only endpoint")
        raise HTTPException(
            status_code=403,
            detail="Authentication required. Please sign up or log in to access this feature."
        )
    return user


def check_feature_access(feature: str):
    """
    Dependency to check if user has access to a specific feature.
    Anonymous users have limited access.
    """
    async def _check_access(user: dict = Depends(get_current_user_or_anonymous)):
        if not user.get("is_authenticated"):
            restricted_features = [
                "save_chat",
                "view_history",
                "create_project",
                "join_group",
                "upload_document",
                "create_assistant",
                "share_conversation",
                "export_data",
                "create_company",
                "manage_team"
            ]

            if feature in restricted_features:
                logger.warning(f"Anonymous user attempted restricted feature: {feature}")
                raise HTTPException(
                    status_code=403,
                    detail=f"This feature requires authentication. Please sign up or log in to use '{feature}'."
                )

        return user

    return _check_access
