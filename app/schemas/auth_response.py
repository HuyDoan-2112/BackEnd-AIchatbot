from pydantic import field_validator, BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional

class UserPublic(BaseModel):
    id: str
    username: str
    email: EmailStr

class SignUpResponse(BaseModel):
    user: UserPublic
    message: str = "User registered successfully"

class AuthTokens(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class LoginResponse(AuthTokens):
    user: Optional[UserPublic] = None