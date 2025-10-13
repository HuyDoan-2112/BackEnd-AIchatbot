from fastapi import APIRouter
from app.api import (
    auth_routes,
    chat_routes,
    company_routes,
    embedding_routes,
    mcp_routes,
    model_routes,
    project_routes,
    retrieval_routes,
    user_routes,
)


router = APIRouter()


router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
router.include_router(chat_routes.router, prefix="/chat", tags=["Chat"])
router.include_router(project_routes.router, prefix="/projects", tags=["Projects"])
router.include_router(model_routes.router, prefix="/models", tags=["Models"])
router.include_router(embedding_routes.router, prefix="/embeddings", tags=["Embeddings"])
#router.include_router(similarity_routes.router, prefix="/similarity", tags=["Similarity"])
router.include_router(retrieval_routes.router, prefix="/retrieval", tags=["Retrieval & RAG"])


router.include_router(user_routes.router, prefix="/users", tags=["Users"])
router.include_router(mcp_routes.router, prefix="/mcp", tags=["MCP"])
router.include_router(company_routes.router, prefix="/company", tags=["Company"])
