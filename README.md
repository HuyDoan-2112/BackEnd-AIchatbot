# RAG Application

Retrieval-Augmented Generation API built with FastAPI and LangChain.

## Project Structure

```
RAG/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoint definitions
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration and settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── factory.py          # Vector store factory
│   │   └── vector_store.py     # Vector store implementations
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── document.py         # Pydantic schemas for validation
│   └── services/
│       ├── __init__.py
│       ├── document_service.py # Document management logic
│       └── rag_service.py      # RAG chain logic
├── docker-compose.yaml         # Docker configuration
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables (create this)
```

## Setup

1. Create `.env` file with required variables:
```env
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_db
DB_HOST=localhost
DB_PORT=5432
OPENAI_API_KEY=your_openai_key
USE_ASYNC=true
COLLECTION_NAME=testcollection
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start database:
```bash
docker-compose up -d
```

4. Run application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /api/v1/documents/` - Add documents
- `GET /api/v1/documents/ids/` - Get all document IDs
- `POST /api/v1/documents/query/` - Get documents by IDs
- `DELETE /api/v1/documents/` - Delete documents
- `POST /api/v1/chat/` - Chat with RAG

## Files to Remove

The following old files can be safely deleted after migration:
- `main.py` (root level - replaced by app/main.py)
- `models.py` (replaced by app/schemas/document.py)
- `myrequest.py` (test file - can be rewritten)
- `store.py` (replaced by app/db/vector_store.py)
- `store_factory.py` (replaced by app/db/factory.py)
