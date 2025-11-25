#!/bin/bash
echo "========================================"
echo "   MAMAS RAG Backend Server"
echo "========================================"
echo ""
echo "Starting server..."
echo "Server will be available at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

