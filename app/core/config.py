"""
Application configuration and environment variables.
"""
import os
from functools import lru_cache
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings
from langchain.chat_models import init_chat_model

from app.schemas.common import Model


load_dotenv(find_dotenv())


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_HOST: str
    DB_PORT: str

    # OpenAI settings
    OPENAI_API_KEY: str

    # Model settings
    MODEL_NAME: str = "openai/gpt-oss-20b"
    MODEL_BASE_URL: Optional[str] = None  # For local models like LM Studio
    MODEL_PROVIDER: str = "organization_owner"
    MODEL_CONTEXT_WINDOW: int = 4096
    MODEL_COMPLETION_RESERVE: int = 512
    MODEL_TEMPERATURE: float = 0.7
    MODEL_MAX_OUTPUT_TOKENS: int = 512
    MODEL_OWNED_BY: str = "organization_owner"

    # Application settings
    USE_ASYNC: bool = False

    # Vector store settings
    COLLECTION_NAME: str = "testcollection"
    RETRIEVAL_TOP_K: int = 3
    RETRIEVAL_HOST: str = "http://localhost:6333"

    # JWT Authentication settings
    SECRET_KEY: str = "your-secret-key-change-in-production-make-it-very-long-and-random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Embedding settings
    EMBEDDING_MODEL_NAME: Optional[str] = "text-embedding-embeddinggemma-300m"
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_PROVIDER: str = "organization_owner"
    EMBEDDING_OWNED_BY: str = "organization_owner"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
