from fastapi import APIRouter
from app.api import auth_routes, chat_routes

router = APIRouter()


router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
router.include_router(chat_routes.router, prefix="/chat", tags=["Chat"])

# Commented out until document models are fixed
# OpenAI-compatible routes
# router.include_router(models_routes.router, prefix="/models", tags=["Models"])
# router.include_router(embedding_routes.router, prefix="/embeddings", tags=["Embeddings"])

# RAG and retrieval routes
# router.include_router(retrieval_routes.router, prefix="/retrieval", tags=["Retrieval & RAG"])
