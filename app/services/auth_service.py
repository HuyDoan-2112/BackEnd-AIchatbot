from app.repository.user_repository import UserRepository
from app.core.response_status import *
from app.core.jwt import *
from app.core.logger import get_logger

logger = get_logger("auth_service")

class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()
        logger.debug("AuthService initialized")

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
        logger.info(f"Login attempt for email: {email}")
        try:
            checked_user = await self.user_repository.get_user_by_email(email)

            # Check if user exists or if there was an error
            if isinstance(checked_user, (UserNotFound, InternalError)):
                logger.warning(f"Login failed for {email}: User not found or error occurred")
                return checked_user

            if not checked_user:
                logger.warning(f"Login failed for {email}: User not found")
                return UserNotFound(message="User not found", error_code="4004")

            # Verify password
            if not verify_password(password, checked_user['hashed_password']):
                logger.warning(f"Login failed for {email}: Invalid password")
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
                logger.error(f"Login failed for {email}: Could not save refresh token")
                return save_result
            if isinstance(save_result, ResponseStatus) and not save_result.success:
                logger.error(f"Login failed for {email}: Could not save refresh token")
                return save_result

            logger.info(f"Login successful for user: {checked_user['username']} ({email})")
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
            logger.error(f"Login exception for {email}: {str(e)}", exc_info=True)
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

            if isinstance(result, ResponseStatus):
                if not result.success:
                    return result
                user_data = result.data or {}
            elif isinstance(result, dict) and result.get("success"):
                # Backwards compatibility if repository returns dict
                user_data = result.get("data") or {}
            else:
                return NotFound(message="Invalid or expired refresh token", error_code="4004")

            if not user_data:
                return InvalidToken(message="Invalid refresh token", error_code="4012")

            access_token = create_access_token(data={"sub": str(user_data["id"])})

            return OK(
                message="Token refreshed successfully",
                data={
                    "access_token": access_token,
                    "user": user_data,
                },
            )
        except Exception as e:
            return InternalError(message=f"Failed to refresh token: {str(e)}", error_code="5000")
    
    async def signup(self, username: str, email: str, password: str):
        """Register a new user"""
        logger.info(f"Signup attempt for username: {username}, email: {email}")
        try:
            # Validate input
            if not username or not email or not password:
                logger.warning(f"Signup failed: Missing required fields")
                return ValidationError(message="Username, email, and password are required", error_code="4002")

            if len(password) < 8:
                logger.warning(f"Signup failed for {username}: Password too short")
                return ValidationError(message="Password must be at least 8 characters long", error_code="4002")

            # Hash password
            logger.debug(f"Hashing password for user: {username}")
            hashed_password = get_password_hash(password)

            # Generate tokens
            from datetime import datetime, timedelta
            refresh_token = create_refresh_token(data={"sub": email})  # Temporary, will be replaced after user creation
            expires_at = int((datetime.utcnow() + timedelta(days=7)).timestamp())

            # Create user
            logger.debug(f"Creating user in database: {username}")
            result = await self.user_repository.create_user(
                username=username,
                email=email,
                hashed_password=hashed_password,
                refresh_token=refresh_token,
                refresh_token_expires_at=expires_at
            )

            # Handle error responses
            if isinstance(result, (BadRequest, InternalError)):
                logger.error(f"Signup failed for {username}: {result.message if hasattr(result, 'message') else 'Unknown error'}")
                return result

            # Extract user data and generate proper tokens
            # Check if result is a ResponseStatus object (like OK)
            if isinstance(result, ResponseStatus):
                user_data = result.data
            elif isinstance(result, dict) and result.get('success'):
                user_data = result.get('data')
            else:
                return InternalError(message="Failed to create user", error_code="5000")

            if not user_data:
                return InternalError(message="Failed to create user", error_code="5000")

            # Generate proper tokens with user ID
            logger.debug(f"Generating tokens for new user: {username}")
            access_token = create_access_token(data={"sub": str(user_data['id'])})
            new_refresh_token = create_refresh_token(data={"sub": str(user_data['id'])})

            # Update refresh token in database
            logger.debug(f"Saving refresh token for user: {username}")
            await self.user_repository.save_refresh_token(
                str(user_data['id']),
                new_refresh_token,
                expires_at
            )

            logger.info(f"Signup successful for user: {username} ({email})")
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
        except Exception as e:
            logger.error(f"Signup exception for {username}: {str(e)}", exc_info=True)
            return InternalError(message=f"Failed to signup: {str(e)}", error_code="5000")
