#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the FastAPI server
echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo "Auth endpoints at: http://localhost:8000/api/v1/auth"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
