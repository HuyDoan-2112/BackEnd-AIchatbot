from app.schemas.auth_request import LoginRequest, SignUpRequest, RefreshTokenRequest
from app.schemas.auth_response import LoginResponse, SignUpResponse, UserPublic
from fastapi import APIRouter, HTTPException, Header, Depends
from app.services import AuthService
from app.core.response_status import *
from typing import Optional


router = APIRouter()
auth_service = AuthService()


@router.post(
    "/signup", # endpoint
    status_code=201,
    summary="Register a new user",
    description="""
    Create a new user account with username, email, and password.

    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()-_=+[]{};:,.?/\\|)

    **Returns:**
    - Access token (valid for 30 minutes)
    - Refresh token (valid for 7 days)
    - User information
    """,
    response_description="User successfully created with authentication tokens",
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User created successfully",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "username": "john_doe",
                                "email": "john@example.com",
                                "created_at": "2025-10-11T12:00:00"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad request - Username/email already exists or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Username or email already exists",
                        "error_code": "4009"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Failed to create user",
                        "error_code": "5000"
                    }
                }
            }
        }
    }
)
async def signup(request: SignUpRequest):
    """
    User signup endpoint.
    Creates a new user account and returns access/refresh tokens.
    """
    try:
        result = await auth_service.signup(request.username, request.email, request.password)

        # Handle error responses from service
        if isinstance(result, ResponseStatus):
            return result.send()

        # If result is a dict with success key
        if isinstance(result, dict) and result.get('success'):
            return result

        raise HTTPException(status_code=500, detail="Unexpected response from auth service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post(
    "/login",
    summary="Login user",
    description="""
    Authenticate a user with username and password.

    **Returns:**
    - Access token (valid for 30 minutes) - Use this for API requests
    - Refresh token (valid for 7 days) - Use this to get new access tokens
    - User information

    **Usage:**
    1. Send username and password
    2. Store both tokens securely
    3. Use access token in Authorization header: `Bearer <access_token>`
    4. When access token expires, use refresh token to get a new one
    """,
    response_description="Login successful with authentication tokens",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Login successful",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "username": "john_doe",
                                "email": "john@example.com"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Invalid credentials",
                        "error_code": "4001"
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "User not found",
                        "error_code": "4004"
                    }
                }
            }
        }
    }
)
async def login(request: LoginRequest):
    """
    User login endpoint.
    Authenticates user and returns access/refresh tokens.
    """
    try:
        result = await auth_service.login(request.email, request.password)

        # Handle error responses from service
        if isinstance(result, ResponseStatus):
            return result.send()

        # If result is a dict with success key
        if isinstance(result, dict) and result.get('success'):
            return result

        raise HTTPException(status_code=500, detail="Unexpected response from auth service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post(
    "/refresh",
    summary="Refresh access token",
    description="""
    Get a new access token using a valid refresh token.

    **When to use:**
    - When your access token expires (after 30 minutes)
    - Before the refresh token expires (7 days)

    **What you get:**
    - New access token (valid for 30 minutes)
    - User information

    **Note:** The refresh token itself is not renewed. When it expires, user must login again.
    """,
    response_description="New access token generated successfully",
    responses={
        200: {
            "description": "Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Token refreshed successfully",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "username": "john_doe",
                                "email": "john@example.com"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid or expired refresh token",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Invalid or expired refresh token",
                        "error_code": "4012"
                    }
                }
            }
        }
    }
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Token refresh endpoint.
    Generates a new access token using a valid refresh token.
    """
    try:
        result = await auth_service.refresh_token(request.refresh_token)

        # Handle error responses from service
        if isinstance(result, ResponseStatus):
            return result.send()

        # If result is a dict with success key
        if isinstance(result, dict) and result.get('success'):
            return result

        raise HTTPException(status_code=500, detail="Unexpected response from auth service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


@router.post(
    "/logout",
    summary="Logout user",
    description="""
    Logout user by invalidating their refresh token.

    **Required Header:**
    ```
    Authorization: Bearer <refresh_token>
    ```

    **What happens:**
    - Refresh token is invalidated
    - User must login again to get new tokens
    - Active access tokens will continue to work until they expire

    **Security Note:** For complete logout, frontend should:
    1. Call this endpoint
    2. Delete stored tokens from local storage
    3. Redirect to login page
    """,
    response_description="Logout successful",
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Logout successful"
                    }
                }
            }
        },
        401: {
            "description": "Authorization header missing or invalid",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Authorization header required"
                    }
                }
            }
        },
        404: {
            "description": "Token not found or already invalidated",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Token not found or already invalidated",
                        "error_code": "4004"
                    }
                }
            }
        }
    }
)
async def logout(authorization: Optional[str] = Header(None)):
    """
    User logout endpoint.
    Invalidates the refresh token.
    Expects Authorization header: Bearer <token>
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "").strip()

        if not token:
            raise HTTPException(status_code=401, detail="Token required")

        result = await auth_service.logout(token)

        # Handle error responses from service
        if isinstance(result, ResponseStatus):
            return result.send()

        # If result is a dict with success key
        if isinstance(result, dict) and result.get('success'):
            return result

        raise HTTPException(status_code=500, detail="Unexpected response from auth service")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@router.get(
    "/verify",
    summary="Verify access token",
    description="""
    Verify if an access token is valid and not expired.

    **Required Header:**
    ```
    Authorization: Bearer <access_token>
    ```

    **Use this endpoint to:**
    - Check if user is authenticated
    - Validate token before making sensitive operations
    - Get current user's ID from token

    **Returns:**
    - Token validity status
    - User ID if token is valid
    """,
    response_description="Token is valid",
    responses={
        200: {
            "description": "Token is valid",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Token is valid",
                        "data": {
                            "user_id": "123e4567-e89b-12d3-a456-426614174000"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Token is invalid or expired",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_header": {
                            "summary": "Missing Authorization header",
                            "value": {
                                "detail": "Authorization header required"
                            }
                        },
                        "expired_token": {
                            "summary": "Token expired",
                            "value": {
                                "success": False,
                                "message": "Token has expired",
                                "error_code": "4011"
                            }
                        },
                        "invalid_token": {
                            "summary": "Invalid token",
                            "value": {
                                "success": False,
                                "message": "Invalid token",
                                "error_code": "4012"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify token endpoint.
    Checks if the provided access token is valid.
    Expects Authorization header: Bearer <token>
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "").strip()

        if not token:
            raise HTTPException(status_code=401, detail="Token required")

        result = await auth_service.verify_token(token)

        # Handle error responses from service
        if isinstance(result, ResponseStatus):
            return result.send()

        # If result is a dict with success key
        if isinstance(result, dict) and result.get('success'):
            return result

        raise HTTPException(status_code=500, detail="Unexpected response from auth service")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")