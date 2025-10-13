from fastapi import APIRouter, HTTPException, status
import time
import base64
import struct

from app.schemas.embedding import (
    EmbeddingRequest,
    EmbeddingResponse,
    Embedding,
    EmbeddingUsage
)
from app.schemas.common import ErrorResponse, ErrorDetail
from app.services.embedding_service import embedding_service

router = APIRouter()


@router.post(
    "",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Create embeddings",
    description="Creates an embedding vector representing the input text (OpenAI-compatible)",
    responses={
        200: {"description": "Successful embedding generation"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_embeddings(request: EmbeddingRequest):
    """
    Create embeddings (OpenAI-compatible endpoint).
    
    This endpoint is compatible with OpenAI's embeddings API.
    
    Example request:
    ```json
    {
        "model": "text-embedding-ada-002",
        "input": "The quick brown fox jumps over the lazy dog",
        "encoding_format": "float"
    }
    ```
    
    Or with multiple inputs:
    ```json
    {
        "model": "text-embedding-ada-002",
        "input": [
            "First text to embed",
            "Second text to embed"
        ]
    }
    ```
    """
    try:
        response = await embedding_service.create_embeddings(request)
        return response
        
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "message": str(e),
                    "type": "not_implemented_error",
                    "code": "service_not_implemented"
                }
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": str(e),
                    "type": "invalid_request_error",
                    "code": "invalid_request"
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "message": f"An error occurred: {str(e)}",
                    "type": "internal_server_error",
                    "code": "internal_error"
                }
            }
        )


# Example endpoint for testing - can be removed later
@router.post(
    "/mock",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Mock embeddings (for testing)",
    description="Mock endpoint that returns dummy embeddings for testing"
)
async def mock_embeddings(request: EmbeddingRequest):
    """
    Mock endpoint for testing the API structure.
    Returns dummy embeddings. Can be removed once service layer is implemented.
    """
    import random
    
    # Determine inputs
    if isinstance(request.input, str):
        inputs = [request.input]
    elif isinstance(request.input, list):
        if all(isinstance(i, str) for i in request.input):
            inputs = request.input
        else:
            # Token inputs - convert to string representation
            inputs = ["[tokens]"]
    else:
        inputs = [str(request.input)]
    
    # Generate mock embeddings (1536 dimensions like OpenAI ada-002)
    dimension = request.dimensions if request.dimensions else 1536
    
    embeddings_list = []
    for idx, inp in enumerate(inputs):
        # Generate random embedding
        embedding_vector = [random.uniform(-1, 1) for _ in range(dimension)]
        
        # Convert to base64 if requested
        if request.encoding_format == "base64":
            embedding_data = await embedding_service.encode_base64(embedding_vector)
        else:
            embedding_data = embedding_vector
        
        embeddings_list.append(
            Embedding(
                object="embedding",
                embedding=embedding_data,
                index=idx
            )
        )
    
    # Mock token counting
    total_tokens = sum(len(inp.split()) * 2 for inp in inputs)  # Rough estimate
    
    response = EmbeddingResponse(
        object="list",
        data=embeddings_list,
        model=request.model,
        usage=EmbeddingUsage(
            prompt_tokens=total_tokens,
            total_tokens=total_tokens
        )
    )
    
    return response
