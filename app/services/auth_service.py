from app.repository.user_repository import UserRepository
from app.core.response_status import *
from app.core.jwt import *

class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()

    async def verify_token(self, token_str: str) -> bool:
        """Verify access token"""
        try:
            payload = decode_token(token_str)
            if isinstance(payload, (TokenExpired, InvalidToken)):
                return payload
            user_id = payload.get("sub")
            if not user_id:
                return InvalidToken(message="Invalid token payload", error_code="4012")
            return OK(message="Token is valid", data={"user_id": user_id})
        except Exception as e:
            return InternalError(message=f"Failed to verify token: {str(e)}", error_code="5000")
    
    async def generate_token(self, user_id: str) -> str:
        """Generate access and refresh tokens for a user"""
        try:
            access_token = create_access_token(data={"sub": user_id})
            refresh_token = create_refresh_token(data={"sub": user_id})
            return OK(message="Tokens generated successfully", data={
                "access_token": access_token,
                "refresh_token": refresh_token
            })
        except Exception as e:
            return InternalError(message=f"Failed to generate tokens: {str(e)}", error_code="5000")
    
    async def login(self, email: str, password: str):
        """Login user and generate access token"""
        try:
            checked_user = await self.user_repository.get_user_by_email(email)

            # Check if user exists or if there was an error
            if isinstance(checked_user, (UserNotFound, InternalError)):
                return checked_user

            if not checked_user:
                return UserNotFound(message="User not found", error_code="4004")

            # Verify password
            if not verify_password(password, checked_user['hashed_password']):
                return InvalidCredentials(message="Invalid credentials", error_code="4001")

            # Generate tokens
            access_token = create_access_token(data={"sub": str(checked_user['id'])})
            refresh_token = create_refresh_token(data={"sub": str(checked_user['id'])})

            # Calculate expiration time for refresh token (in unix timestamp)
            from datetime import datetime, timedelta
            expires_at = int((datetime.utcnow() + timedelta(days=7)).timestamp())

            # Save refresh token in DB
            save_result = await self.user_repository.save_refresh_token(
                str(checked_user['id']),
                refresh_token,
                expires_at
            )

            if isinstance(save_result, InternalError):
                return save_result

            return OK(message="Login successful", data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(checked_user['id']),
                    "username": checked_user['username'],
                    "email": checked_user['email']
                }
            })
        except Exception as e:
            return InternalError(message=f"Failed to login: {str(e)}", error_code="5000")

    async def logout(self, token_str: str) -> None:
        """Logout user by invalidating refresh token"""
        try:
            # Decode token to get user info
            payload = decode_token(token_str)
            if isinstance(payload, (TokenExpired, InvalidToken)):
                return payload

            user_id = payload.get("sub")
            if not user_id:
                return InvalidToken(message="Invalid token payload", error_code="4012")

            # Invalidate the refresh token
            result = await self.user_repository.invalidate_token(token_str)

            if isinstance(result, InternalError):
                return result

            if result:
                return OK(message="Logout successful")
            else:
                return NotFound(message="Token not found or already invalidated", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to logout: {str(e)}", error_code="5000")
    
    async def refresh_token(self, token_str: str) -> str:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            result = await self.user_repository.verify_refresh_token(token_str)

            # Handle error responses
            if isinstance(result, (NotFound, InternalError)):
                return result

            # If result is a response object, extract user data
            if isinstance(result, dict) and result.get('success'):
                user_data = result.get('data')
                if not user_data:
                    return InvalidToken(message="Invalid refresh token", error_code="4012")

                # Generate new access token
                access_token = create_access_token(data={"sub": str(user_data['id'])})

                return OK(message="Token refreshed successfully", data={
                    "access_token": access_token,
                    "user": user_data
                })
            else:
                return NotFound(message="Invalid or expired refresh token", error_code="4004")
        except Exception as e:
            return InternalError(message=f"Failed to refresh token: {str(e)}", error_code="5000")
    
    async def signup(self, username: str, email: str, password: str):
        """Register a new user"""
        try:
            # Validate input
            if not username or not email or not password:
                return ValidationError(message="Username, email, and password are required", error_code="4002")

            if len(password) < 8:
                return ValidationError(message="Password must be at least 8 characters long", error_code="4002")

            # Hash password
            hashed_password = get_password_hash(password)

            # Generate tokens
            from datetime import datetime, timedelta
            refresh_token = create_refresh_token(data={"sub": email})  # Temporary, will be replaced after user creation
            expires_at = int((datetime.utcnow() + timedelta(days=7)).timestamp())

            # Create user
            result = await self.user_repository.create_user(
                username=username,
                email=email,
                hashed_password=hashed_password,
                refresh_token=refresh_token,
                refresh_token_expires_at=expires_at
            )

            # Handle error responses
            if isinstance(result, (BadRequest, InternalError)):
                return result

            # Extract user data and generate proper tokens
            if isinstance(result, dict) and result.get('success'):
                user_data = result.get('data')
                if not user_data:
                    return InternalError(message="Failed to create user", error_code="5000")

                # Generate proper tokens with user ID
                access_token = create_access_token(data={"sub": str(user_data['id'])})
                new_refresh_token = create_refresh_token(data={"sub": str(user_data['id'])})

                # Update refresh token in database
                await self.user_repository.save_refresh_token(
                    str(user_data['id']),
                    new_refresh_token,
                    expires_at
                )

                return Created(message="User created successfully", data={
                    "access_token": access_token,
                    "refresh_token": new_refresh_token,
                    "user": {
                        "id": str(user_data['id']),
                        "username": user_data['username'],
                        "email": user_data['email'],
                        "created_at": user_data['created_at']
                    }
                })
            else:
                return InternalError(message="Failed to create user", error_code="5000")
        except Exception as e:
            return InternalError(message=f"Failed to signup: {str(e)}", error_code="5000")


