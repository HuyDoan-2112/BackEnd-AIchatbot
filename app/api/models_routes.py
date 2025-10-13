"""
OpenAI-compatible Models API Routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
import time

from app.schemas.common import Model, ModelListResponse
from app.core.model_registry import get_model_registry, ModelRegistry

router = APIRouter()


@router.get(
    "",
    response_model=ModelListResponse,
    status_code=status.HTTP_200_OK,
    summary="List models",
    description="Lists the currently available models (OpenAI-compatible)",
)
async def list_models(registry: ModelRegistry = Depends(get_model_registry)):
    """
    List available models (OpenAI-compatible endpoint).
    
    Returns a list of models that can be used with the API.
    Includes the currently loaded model from .env
    
    Example response:
    ```json
    {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            }
        ]
    }
    ```
    """
    current_time = int(time.time())
    available = registry.list_chat_models()

    models = [
        Model(
            id=model["id"],
            object="model",
            created=current_time,
            owned_by=model.get("owned_by", "custom")
        )
        for model in available
    ]

    return ModelListResponse(
        object="list",
        data=models
    )


@router.get(
    "/{model_id}",
    response_model=Model,
    status_code=status.HTTP_200_OK,
    summary="Retrieve model",
    description="Retrieves a model instance (OpenAI-compatible)",
)
async def retrieve_model(model_id: str):
    """
    Retrieve a specific model by ID (OpenAI-compatible endpoint).
    
    Example response:
    ```json
    {
        "id": "gpt-3.5-turbo",
        "object": "model",
        "created": 1677610602,
        "owned_by": "openai"
    }
    ```
    """
    # Find model in default list
    available = registry.list_chat_models()
    model_data = next((m for m in available if m["id"] == model_id), None)

    if not model_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Model '{model_id}' not found",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }
        )
    
    return Model(
        id=model_data["id"],
        object="model",
        created=int(time.time()),
        owned_by=model_data.get("owned_by", "custom")
    )
