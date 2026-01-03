# Setup Checklist

Use this checklist to track your setup progress.

## Prerequisites

- [ ] Node.js 20+ installed (`node --version`)
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] PostgreSQL 15+ installed or Docker available
- [ ] Redis 7+ installed or Docker available
- [ ] FFmpeg installed (`ffmpeg -version`)
- [ ] Git installed

## Infrastructure

- [ ] PostgreSQL is running
  ```bash
  pg_isready
  # Or: docker-compose up -d postgres
  ```
- [ ] Redis is running
  ```bash
  redis-cli ping
  # Or: docker-compose up -d redis
  ```
- [ ] Database `reelestate` created
  ```bash
  createdb reelestate
  # Or via Docker
  ```

## Backend Setup

- [ ] Virtual environment created
  ```bash
  cd backend && python3 -m venv venv
  ```
- [ ] Virtual environment activated
  ```bash
  source venv/bin/activate
  ```
- [ ] Dependencies installed
  ```bash
  pip install -e ".[dev]"
  ```
- [ ] `.env` file created from `.env.example`
- [ ] API keys added to `.env`:
  - [ ] `OPENAI_API_KEY`
  - [ ] `FAL_KEY`
  - [ ] `ELEVENLABS_API_KEY` (optional)
  - [ ] `AWS_ACCESS_KEY_ID` (optional)
  - [ ] `AWS_SECRET_ACCESS_KEY` (optional)
- [ ] Database migrations run
  ```bash
  alembic upgrade head
  ```
- [ ] Backend starts without errors
  ```bash
  uvicorn app.main:app --reload
  ```
- [ ] Health check works
  ```bash
  curl http://localhost:8000/health
  ```

## Frontend Setup

- [ ] Dependencies installed
  ```bash
  cd frontend && npm install
  ```
- [ ] `.env.local` file created from `.env.example`
- [ ] Environment variables set in `.env.local`:
  - [ ] `NEXT_PUBLIC_API_URL`
  - [ ] `NEXTAUTH_SECRET`
- [ ] Frontend starts without errors
  ```bash
  npm run dev
  ```
- [ ] Frontend loads at http://localhost:3000

## Worker Setup

- [ ] Celery worker starts without errors
  ```bash
  celery -A app.workers.celery_app worker --loglevel=info
  ```
- [ ] Worker can connect to Redis
- [ ] Tasks can be registered
  ```bash
  celery -A app.workers.celery_app inspect registered
  ```

## Testing

- [ ] Can access API docs: http://localhost:8000/api/docs
- [ ] Can register a new user account
- [ ] Can log in with created account
- [ ] Can create a brand kit
- [ ] Can create a property listing
- [ ] Can create a project
- [ ] Can upload photos
- [ ] Can generate a script (requires OpenAI key)
- [ ] Can queue a video render job (requires fal.ai key)

## Optional Services

- [ ] Stripe configured (for payments)
- [ ] AWS S3 configured (for media storage)
- [ ] HeyGen configured (for avatar generation)
- [ ] Google OAuth configured (for social login)

## Verification Commands

Run these to verify everything works:

```bash
# Backend health
curl http://localhost:8000/health

# Database connection
psql -U postgres -d reelestate -c "SELECT 1;"

# Redis connection
redis-cli ping

# Frontend build
cd frontend && npm run build

# Python imports
cd backend && source venv/bin/activate && python -c "from app.main import app; print('OK')"
```

## All Done! ✅

Once all items are checked:
- [ ] All services running
- [ ] Can create and render a project
- [ ] Video generation works (with fal.ai key)

---

**Next Steps:**
1. Read the [API documentation](http://localhost:8000/api/docs)
2. Explore the [dashboard](http://localhost:3000/dashboard)
3. Create your first property tour video!

