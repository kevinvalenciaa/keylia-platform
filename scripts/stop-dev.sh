#!/bin/bash

# ReelEstate Studio - Stop Development Services

echo "🛑 Stopping ReelEstate Studio Development Services"
echo "==================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Stop services by PID
if [ -f logs/backend.pid ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓ Stopped backend (PID: $BACKEND_PID)${NC}"
    fi
    rm logs/backend.pid
fi

if [ -f logs/worker.pid ]; then
    WORKER_PID=$(cat logs/worker.pid)
    if kill -0 $WORKER_PID 2>/dev/null; then
        kill $WORKER_PID
        echo -e "${GREEN}✓ Stopped worker (PID: $WORKER_PID)${NC}"
    fi
    rm logs/worker.pid
fi

if [ -f logs/frontend.pid ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✓ Stopped frontend (PID: $FRONTEND_PID)${NC}"
    fi
    rm logs/frontend.pid
fi

# Also kill any remaining processes on our ports
echo "Cleaning up processes on ports 8000, 3000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"

