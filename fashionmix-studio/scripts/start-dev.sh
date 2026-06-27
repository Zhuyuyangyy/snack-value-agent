#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

# Start backend in background
cd backend
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
echo "Starting backend on :8001..."
uvicorn app:app --port 8001 --reload &
BACKEND_PID=$!

# Start frontend in background — serve from PROJECT ROOT so data/products.json resolves
cd ..
echo "Starting frontend on :8000 (serving from project root)..."
python -m http.server 8000 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
echo ""
echo "==========================================="
echo "Frontend: http://localhost:8000/frontend/index.html"
echo "Backend:  http://localhost:8001"
echo "==========================================="
echo "Press Ctrl+C to stop"
wait