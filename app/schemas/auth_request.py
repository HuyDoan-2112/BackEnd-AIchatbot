from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, model_validator
import re

class SignUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limitation
    confirm_password: str = Field(min_length=8, max_length=72)
    
    @field_validator("username")
    @classmethod
    def username_chars(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_.]+", v):
            raise ValueError("Username may contain letters, digits, underscore, and dot only")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        # Check byte length for bcrypt compatibility
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password cannot be longer than 72 bytes")
        if not any(c.islower() for c in v): raise ValueError("Password needs a lowercase letter")
        if not any(c.isupper() for c in v): raise ValueError("Password needs an uppercase letter")
        if not any(c.isdigit() for c in v): raise ValueError("Password needs a digit")
        if not any(c in "!@#$%^&*()-_=+[]{};:,.?/\\|" for c in v):
            raise ValueError("Password needs a special character")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limitation


class RefreshTokenRequest(BaseModel):
    refresh_token: str
