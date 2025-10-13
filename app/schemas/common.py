"""
Common OpenAI-compatible Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Dict
from datetime import datetime


class ErrorDetail(BaseModel):
    """Error detail"""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """OpenAI-compatible error response"""
    error: ErrorDetail


class Model(BaseModel):
    """Model information"""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ModelListResponse(BaseModel):
    """List of available models"""
    object: Literal["list"] = "list"
    data: List[Model]


class DeleteResponse(BaseModel):
    """Generic delete response"""
    id: str
    object: str
    deleted: bool


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "unhealthy"]
    timestamp: str
    services: Optional[Dict[str, str]] = None
    version: Optional[str] = None
