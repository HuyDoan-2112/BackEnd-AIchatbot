"""
Authentication dependencies for protected routes.
"""
from fastapi import Header, HTTPException, Depends
from typing import Optional
from app.core.jwt import decode_token
from app.core.response_status import TokenExpired, InvalidToken
from app.core.model_registry import get_model_registry, ModelRegistry
from app.core.config import get_settings, Settings


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
