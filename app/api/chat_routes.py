from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
import time
import uuid

from app.schemas.chat_response import (
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
from app.core.dependencies import get_current_user_or_anonymous, get_current_user
from typing import Optional
from app.core.logger import get_logger

logger = get_logger("chat_routes")
router = APIRouter()


def _send_status(result):
    """Normalize ResponseStatus or raw payload to a FastAPI response."""
    try:
        # Chat service uses ResponseStatus for most helpers
        from app.core.response_status import ResponseStatus
        if isinstance(result, ResponseStatus):
            return result.send()
        # Fallback: wrap plain data
        from app.core.response_status import OK
        return OK(data=result).send()
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected service response")


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create chat completion (Anonymous & Authenticated)",
    description="""
    Creates a model response for the given chat conversation (OpenAI-compatible).

    **Anonymous Users:**
    - Can chat without authentication
    - Chat history is NOT saved
    - No access to projects, documents, or advanced features

    **Authenticated Users:**
    - Full access to all features
    - Chat history can be saved
    - Access to projects, documents, and collaboration features
    """,
    responses={
        200: {"description": "Successful completion"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    user: dict = Depends(get_current_user_or_anonymous)
):
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
    # Log user type
    user_type = "authenticated" if user.get("is_authenticated") else "anonymous"
    logger.info(f"Chat completion request from {user_type} user (session: {user.get('session_id')})")

    try:
        # Attach authenticated user to request for persistence
        try:
            if user.get("is_authenticated") and not request.user:
                request.user = user.get("user_id")
        except Exception:
            pass

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


async def stream_chat_completion(request: ChatCompletionRequest):
    """
    Helper function to stream chat completion responses as SSE.
    """
    async def event_generator():
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
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
    
@router.post(
    "/completions/stream",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Stream chat completion",
    description="Streams a model response for the given chat conversation (OpenAI-compatible)",
    responses={
        200: {"description": "Successful streaming completion"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def stream_chat_completion_endpoint(request: ChatCompletionRequest):
    """
    Stream chat completion (OpenAI-compatible endpoint).
    
    This endpoint is compatible with OpenAI's chat completion API for streaming responses.
    
    Example request:
    ```json
    {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 150,
        "stream": true
    }
    ```
    
    The response will be sent as Server-Sent Events (SSE).
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": "`stream` must be true for this endpoint.",
                    "type": "invalid_request_error",
                    "code": "invalid_request"
                }
            }
        )
    
    try:
        return await stream_chat_completion(request)
        
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

@router.get(
    "/conversations",
    summary="List my conversations",
    description="List conversations for the authenticated user (creator or participant).",
)
async def list_my_conversations(
    project_id: Optional[str] = None,
    company_id: Optional[str] = None,
    limit: int = 50,
    current_user: str = Depends(get_current_user),
):
    result = await chat_service.list_user_conversations(
        current_user,
        project_id=project_id,
        company_id=company_id,
        limit=limit,
    )
    return _send_status(result)


@router.get(
    "/conversations/{conversation_id}",
    summary="Get conversation",
    description="Get conversation details if you are a creator or participant.",
)
async def get_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    result = await chat_service.get_conversation_details(conversation_id, user_id=current_user)
    return _send_status(result)


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="List conversation messages",
    description="List recent messages in a conversation you can access.",
)
async def list_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    include_children: bool = False,
    include_artifacts: bool = False,
    include_usage: bool = False,
    current_user: str = Depends(get_current_user),
):
    result = await chat_service.get_conversation_messages(
        conversation_id,
        user_id=current_user,
        limit=limit,
        include_children=include_children,
        include_artifacts=include_artifacts,
        include_usage=include_usage,
    )
    return _send_status(result)
