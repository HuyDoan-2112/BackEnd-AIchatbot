from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RAGRequest,
    RAGResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    RetrievedDocument
)
from app.schemas.common import ErrorResponse, ErrorDetail
from app.services.retrieval_service import retrieval_service

router = APIRouter()


@router.post(
    "/search",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Search documents",
    description="Retrieve relevant documents from vector store based on query",
    responses={
        200: {"description": "Successful retrieval"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def search_documents(request: RetrievalRequest):
    """
    Search for relevant documents in the vector store.
    
    Example request:
    ```json
    {
        "query": "What is machine learning?",
        "k": 5,
        "search_type": "similarity",
        "score_threshold": 0.7
    }
    ```
    """
    try:
        response = await retrieval_service.retrieve_documents(request)
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


@router.post(
    "/rag",
    response_model=RAGResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG query",
    description="Retrieval-Augmented Generation: retrieve relevant documents and generate answer",
    responses={
        200: {"description": "Successful generation"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def rag_query(request: RAGRequest):
    """
    Perform RAG (Retrieval-Augmented Generation) query.
    
    Retrieves relevant documents and generates an answer using an LLM.
    
    Example request:
    ```json
    {
        "query": "What is machine learning?",
        "k": 4,
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "include_sources": true
    }
    ```
    
    For streaming responses, set `stream: true`.
    """
    try:
        # Handle streaming
        if request.stream:
            async def generate():
                try:
                    async for chunk in retrieval_service.rag_query_stream(request):
                        yield chunk
                    
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
                }
            )
        
        # Handle non-streaming
        response = await retrieval_service.rag_query(request)
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


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document",
    description="Upload and index a document in the vector store",
    responses={
        201: {"description": "Document uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def upload_document(request: DocumentUploadRequest):
    """
    Upload and index a document.
    
    The document will be split into chunks, embedded, and stored in the vector store.
    
    Example request:
    ```json
    {
        "content": "This is the document content...",
        "metadata": {
            "source": "example.pdf",
            "author": "John Doe"
        },
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
    ```
    """
    try:
        response = await retrieval_service.upload_document(request)
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


@router.delete(
    "/documents",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete documents",
    description="Delete documents from vector store by IDs or filter",
    responses={
        200: {"description": "Documents deleted successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def delete_documents(request: DocumentDeleteRequest):
    """
    Delete documents from the vector store.
    
    Can delete by document IDs or by metadata filter.
    
    Example request (by IDs):
    ```json
    {
        "ids": ["doc-id-1", "doc-id-2"]
    }
    ```
    
    Example request (by filter):
    ```json
    {
        "filter": {
            "source": "example.pdf"
        }
    }
    ```
    """
    try:
        response = await retrieval_service.delete_documents(request)
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


# Mock endpoints for testing
@router.post(
    "/search/mock",
    response_model=RetrievalResponse,
    summary="Mock search (for testing)"
)
async def mock_search(request: RetrievalRequest):
    """Mock endpoint for testing retrieval API structure."""
    return RetrievalResponse(
        query=request.query,
        documents=[
            RetrievedDocument(
                id="doc-1",
                content="This is a mock retrieved document.",
                score=0.95
            )
        ],
        count=1,
        search_type=request.search_type.value
    )
