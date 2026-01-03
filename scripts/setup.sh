#!/bin/bash

# ReelEstate Studio - Automated Setup Script
# This script helps set up the development environment

set -e  # Exit on error

echo "🚀 ReelEstate Studio - Setup Script"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found. Please install Node.js 20+${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠ PostgreSQL not found. You'll need to install it or use Docker${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL found${NC}"
fi

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis not found. You'll need to install it or use Docker${NC}"
else
    echo -e "${GREEN}✓ Redis found${NC}"
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠ FFmpeg not found. Video processing may not work${NC}"
else
    echo -e "${GREEN}✓ FFmpeg found${NC}"
fi

echo ""
echo "📦 Setting up backend..."

# Backend setup
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit backend/.env and add your API keys${NC}"
fi

# Run migrations
echo "Running database migrations..."
if [ -d "migrations/versions" ] && [ "$(ls -A migrations/versions)" ]; then
    alembic upgrade head
else
    echo "Creating initial migration..."
    alembic revision --autogenerate -m "Initial migration"
    alembic upgrade head
fi

cd ..

echo ""
echo "📦 Setting up frontend..."

# Frontend setup
cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file from example..."
    cp .env.example .env.local
    echo -e "${YELLOW}⚠ Please edit frontend/.env.local with your settings${NC}"
fi

cd ..

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and add your API keys"
echo "2. Edit frontend/.env.local with your settings"
echo "3. Start PostgreSQL and Redis (or use Docker: docker-compose up -d postgres redis)"
echo "4. Start the services:"
echo "   - Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   - Terminal 2: cd backend && source venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info"
echo "   - Terminal 3: cd frontend && npm run dev"
echo ""
echo "For detailed instructions, see SETUP.md"

