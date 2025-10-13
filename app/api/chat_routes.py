from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import time
import uuid

from app.schemas.chat_responses import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatCompletionChoice,
    ChatMessage,
    ChatRole,
    Usage,
)
from app.schemas.common import ErrorResponse, ErrorDetail
from app.services.chat_service import chat_service

router = APIRouter()


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create chat completion",
    description="Creates a model response for the given chat conversation (OpenAI-compatible)",
    responses={
        200: {"description": "Successful completion"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create a chat completion (OpenAI-compatible endpoint).
    
    This endpoint is compatible with OpenAI's chat completion API.
    
    Example request:
    ```json
    {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 150
    }
    ```
    
    For streaming responses, set `stream: true` and the response will be
    sent as Server-Sent Events (SSE).
    """
    try:
        # Handle streaming
        if request.stream:
            async def generate():
                try:
                    async for chunk in chat_service.create_completion_stream(request):
                        # Format as SSE
                        data = chunk.model_dump_json()
                        yield f"data: {data}\n\n"
                    
                    # Send [DONE] message
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    error_response = ErrorResponse(
                        error=ErrorDetail(
                            message=str(e),
                            type="internal_error",
                            code="stream_error"
                        )
                    )
                    yield f"data: {error_response.model_dump_json()}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Handle non-streaming
        response = await chat_service.create_completion(request)
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
