#!/bin/bash

# Start Backend
echo "Starting FastAPI backend..."
cd backend
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Frontend
echo "Starting Next.js frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=================================="
echo "Bluesky Simulation Platform Running"
echo "=================================="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "=================================="
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
