#!/bin/bash

# Keylia - Start Development Services
# This script starts all development services

set -e

echo "Starting Keylia Development Services"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if services are already running
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}Warning: Port $1 is already in use${NC}"
        return 1
    fi
    return 0
}

# Check ports
echo "Checking ports..."
check_port 8000 || exit 1
check_port 3000 || exit 1
check_port 5432 || exit 1
check_port 6379 || exit 1

echo -e "${GREEN}[OK] All ports available${NC}"
echo ""

# Start services in background
echo "Starting services..."

# Backend API
echo "Starting backend API..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}[OK] Backend started (PID: $BACKEND_PID)${NC}"

# Celery Worker
echo "Starting Celery worker..."
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info > ../logs/worker.log 2>&1 &
WORKER_PID=$!
cd ..
echo -e "${GREEN}[OK] Worker started (PID: $WORKER_PID)${NC}"

# Frontend
echo "Starting frontend..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}[OK] Frontend started (PID: $FRONTEND_PID)${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Save PIDs
echo $BACKEND_PID > logs/backend.pid
echo $WORKER_PID > logs/worker.pid
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo -e "${GREEN}All services started successfully!${NC}"
echo ""
echo "Services:"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/api/docs"
echo "  - Frontend: http://localhost:3000"
echo ""
echo "Logs:"
echo "  - Backend: tail -f logs/backend.log"
echo "  - Worker: tail -f logs/worker.log"
echo "  - Frontend: tail -f logs/frontend.log"
echo ""
echo "To stop all services, run: ./scripts/stop-dev.sh"

