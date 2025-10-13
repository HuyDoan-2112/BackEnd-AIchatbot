"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import OpenAIEmbeddings

from app.api import routes
from app.core.config import get_settings
from app.db import postgresql
from app.core import model_registry as model_registry_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    TODO: Implement startup and shutdown logic.
    - Load settings
    - Initialize embeddings
    - Create vector store
    - Initialize services
    - Store in app.state for dependency injection
    """
    # Startup
    settings = get_settings()
    
    # Initialize model registry
    model_registry_module.model_registry = model_registry_module.ModelRegistry(settings)
    await model_registry_module.model_registry.initialize()
    print(f"✓ Model registry initialized with model: {settings.MODEL_NAME}")


    postgresql.db_connection = postgresql.PostgreSQLConnection(settings.database_url)
    await postgresql.db_connection.connect()

    # Initialize embeddings
    # embeddings = OpenAIEmbeddings()

    # Create vector store
    # mode = "async" if settings.USE_ASYNC else "sync"
    # vector_store = get_vector_store(
    #     connection_string=settings.database_url,
    #     embeddings=embeddings,
    #     collection_name=settings.COLLECTION_NAME,
    #     mode=mode,
    # )

    # Initialize services
    # document_service = DocumentService(vector_store)
    # rag_service = RAGService(vector_store)

    # Store services in app state
    # app.state.document_service = document_service
    # app.state.rag_service = rag_service
    # app.state.db_connection = postgresql.db_connection

    yield

    # Shutdown
    await model_registry_module.model_registry.shutdown()
    await postgresql.db_connection.close()
    print("✓ Database connection closed")


# Create FastAPI application with enhanced Swagger documentation
app = FastAPI(
    title="RAG Application API",
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="http://example.com/terms/",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication operations including signup, login, logout, and token management.",
        },
        {
            "name": "Chat",
            "description": "AI-powered chat operations with document context using RAG.",
        },
        {
            "name": "Embeddings",
            "description": "Generate embeddings for text and documents.",
        },
        {
            "name": "Retrieval & RAG",
            "description": "Semantic search and retrieval operations using vector embeddings.",
        },
        {
            "name": "Models",
            "description": "Available AI models and their configurations.",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas section by default
        "docExpansion": "list",  # Expand only tags, not operations
        "filter": True,  # Enable search/filter
        "showCommonExtensions": True,
        "syntaxHighlight.theme": "monokai",  # Code syntax highlighting theme
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.0.246:5173",
        "https://qwg237dx-5173.use.devtunnels.ms"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api/v1")

