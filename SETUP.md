# ReelEstate Studio - Local Development Setup Guide

This guide will walk you through setting up the entire ReelEstate Studio platform on your local machine.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

1. **Node.js 20+** and npm
   ```bash
   node --version  # Should be 20.x or higher
   npm --version
   ```

2. **Python 3.11+**
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

3. **Supabase Account** (Recommended - Free tier available)
   - Sign up at https://supabase.com
   - Create a new project
   - Get your database connection string

   **OR** Local PostgreSQL 15+ (Alternative)
   ```bash
   psql --version  # Should be 15.x or higher
   ```

4. **Redis 7+** (or use Upstash Redis Cloud - free tier)
   ```bash
   redis-cli --version  # Should be 7.x or higher
   ```

5. **FFmpeg** (for video processing)
   ```bash
   ffmpeg -version
   ```

6. **Docker & Docker Compose** (optional, for Redis only)
   ```bash
   docker --version
   docker-compose --version
   ```

### Installation Links

- **Node.js**: https://nodejs.org/
- **Python**: https://www.python.org/downloads/
- **Supabase**: https://supabase.com (Recommended - includes PostgreSQL)
- **PostgreSQL**: https://www.postgresql.org/download/ (Alternative)
- **Redis**: https://redis.io/download or https://upstash.com (Cloud option)
- **FFmpeg**: https://ffmpeg.org/download.html
- **Docker**: https://www.docker.com/get-started

---

## 🚀 Quick Start (Supabase Method - Recommended)

Using Supabase eliminates the need to run PostgreSQL locally. This is the easiest setup method.

### Step 1: Create Supabase Project

1. Go to https://supabase.com and sign up/login
2. Click "New Project"
3. Choose organization, name your project (e.g., "reelestate-studio")
4. Set a database password (save this!)
5. Choose a region close to you
6. Wait for project to be created (~2 minutes)

### Step 2: Get Database Connection String

1. In Supabase Dashboard, go to **Settings** → **Database**
2. Scroll to **Connection String** section
3. Select **Connection Pooling** tab
4. Copy the **URI** connection string
   - It looks like: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
5. Replace `postgresql://` with `postgresql+asyncpg://` for async support

### Step 3: Clone and Navigate

```bash
cd keylia-platform
```

### Step 4: Start Redis (or use Upstash Cloud)

**Option A: Local Redis with Docker**
```bash
docker-compose up -d redis
```

**Option B: Upstash Redis Cloud (Free tier)**
1. Go to https://upstash.com
2. Create a Redis database
3. Copy the Redis URL (looks like: `redis://default:password@host:port`)

### Step 5: Configure Environment Variables

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your API keys (see Step 6 below)

# Frontend
cd ../frontend
cp .env.example .env.local
# Edit .env.local (see Step 6 below)
```

### Step 6: Add Your Configuration

Edit `backend/.env` and add:

```env
# Database (from Supabase - Step 2)
DATABASE_URL=postgresql+asyncpg://postgres.[project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Supabase (optional - for additional features)
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Redis (from Step 4)
REDIS_URL=redis://localhost:6379/0
# OR if using Upstash: REDIS_URL=redis://default:password@host:port

# Security
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here

# AI Services (get keys from providers)
OPENAI_API_KEY=sk-your-openai-key
FAL_KEY=your-fal-ai-key
ELEVENLABS_API_KEY=your-elevenlabs-key

# Storage (use Supabase Storage or AWS S3)
# Option 1: Supabase Storage (easier - included with Supabase)
SUPABASE_STORAGE_BUCKET=reelestate-media

# Option 2: AWS S3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=reelestate-media-dev

# Optional (for full functionality)
HEYGEN_API_KEY=your-heygen-key
STRIPE_SECRET_KEY=sk_test_your-stripe-key
```

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret-here
```

### Step 7: Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# If migrations don't exist yet, create initial migration
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Step 8: Setup Frontend

```bash
cd ../frontend

# Install dependencies
npm install
```

### Step 9: Start All Services

You'll need **4 terminal windows**:

#### Terminal 1: Backend API
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2: Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

#### Terminal 3: Frontend
```bash
cd frontend
npm run dev
```

#### Terminal 4: (Optional) Celery Beat (for scheduled tasks)
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info
```

### Step 10: Verify Setup

1. **Backend API**: http://localhost:8000
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/api/docs

2. **Frontend**: http://localhost:3000

3. **Database**: Check Supabase connection
   ```bash
   # Test connection via Python
   cd backend
   source venv/bin/activate
   python -c "
   from app.database import engine
   import asyncio
   async def test():
       async with engine.begin() as conn:
           result = await conn.execute('SELECT 1')
           print('✓ Database connection OK')
   asyncio.run(test())
   "
   ```

4. **Redis**: Check connection
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

---

## 🔧 Alternative: Local PostgreSQL Setup

If you prefer to use local PostgreSQL instead of Supabase:

### Step 1: Setup PostgreSQL

```bash
# Create database
createdb reelestate

# Or using psql:
psql -U postgres
CREATE DATABASE reelestate;
\q
```

### Step 2: Update DATABASE_URL

In `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reelestate
```

### Step 3: Setup Redis

**Option A: Local Redis**
```bash
# Start Redis server
redis-server

# Or on macOS with Homebrew:
brew services start redis

# Or on Linux:
sudo systemctl start redis
```

**Option B: Upstash Redis Cloud (Free)**
1. Go to https://upstash.com
2. Create a Redis database
3. Copy the Redis URL to `backend/.env`

### Step 4: Continue with Steps 7-10 from Supabase Method above

---

## 📝 Detailed Setup Steps

### Backend Setup Details

#### 1. Python Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

#### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

#### 3. Database Migrations

```bash
# Create initial migration (first time only)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Check migration status
alembic current
```

#### 4. Verify Backend

```bash
# Test import
python -c "from app.main import app; print('✓ Backend imports OK')"

# Run tests (if you have any)
pytest
```

### Frontend Setup Details

#### 1. Install Dependencies

```bash
cd frontend
npm install
```

#### 2. Verify Frontend

```bash
# Check for TypeScript errors
npm run build

# Or just start dev server
npm run dev
```

### Worker Setup Details

#### 1. Verify Celery

```bash
cd backend
source venv/bin/activate

# Check Celery can import tasks
celery -A app.workers.celery_app inspect registered
```

#### 2. Test Worker

In a Python shell:
```python
from app.workers.tasks.fal_video import fal_generate_video_task
result = fal_generate_video_task.delay(
    image_url="https://example.com/test.jpg",
    duration_seconds=5.0,
    camera_motion="zoom_in",
    tone="modern",
    model="kling"
)
print(f"Task ID: {result.id}")
```

---

## 🔑 Getting API Keys

### 1. Supabase (for database - FREE)

1. Go to https://supabase.com
2. Sign up / Log in
3. Create a new project
4. Go to **Settings** → **Database**
5. Copy the **Connection Pooling** URI
6. Replace `postgresql://` with `postgresql+asyncpg://`
7. Add to `backend/.env`: `DATABASE_URL=postgresql+asyncpg://...`

**Bonus**: Supabase also provides:
- Free storage (can replace S3)
- Built-in authentication (can replace custom JWT)
- Real-time subscriptions
- Edge functions

### 2. OpenAI (for script generation)

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `backend/.env`: `OPENAI_API_KEY=sk-...`

### 3. fal.ai (for video generation)

1. Go to https://fal.ai/dashboard
2. Sign up / Log in
3. Get your API key from dashboard
4. Add to `backend/.env`: `FAL_KEY=...`

### 4. ElevenLabs (for voiceover)

1. Go to https://elevenlabs.io/
2. Sign up and get API key
3. Add to `backend/.env`: `ELEVENLABS_API_KEY=...`

### 5. Storage (Choose one)

**Option A: Supabase Storage (Recommended - FREE)**
1. In Supabase Dashboard → Storage
2. Create a bucket named `reelestate-media`
3. Set it to public or configure policies
4. No additional keys needed!

**Option B: AWS S3 (Alternative)**

1. Create AWS account
2. Create S3 bucket
3. Create IAM user with S3 permissions
4. Get access key and secret
5. Add to `backend/.env`:
   ```
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket-name
   ```

### 6. Stripe (for payments - optional)

1. Go to https://dashboard.stripe.com/
2. Get test API keys
3. Add to `backend/.env`: `STRIPE_SECRET_KEY=sk_test_...`

---

## 🧪 Testing the Setup

### 1. Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Should return: {"status":"healthy","version":"0.1.0"}
```

### 2. Test Database Connection

```bash
cd backend
source venv/bin/activate
python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('✓ Database connection OK')
asyncio.run(test())
"
```

### 3. Test Redis Connection

```bash
cd backend
source venv/bin/activate
python -c "
import redis
r = redis.from_url('redis://localhost:6379/0')
r.ping()
print('✓ Redis connection OK')
"
```

### 4. Test Frontend

1. Open http://localhost:3000
2. You should see the landing page
3. Try navigating to `/signup`

### 5. Test Video Generation (fal.ai)

```bash
cd backend
source venv/bin/activate
python -c "
from app.services.ai.fal_video_service import FalVideoService, VideoGenerationRequest, VideoModel, CameraMotion
import asyncio

async def test():
    service = FalVideoService()
    # Use a test image URL
    result = await service.generate_video_from_image(
        VideoGenerationRequest(
            image_url='https://images.unsplash.com/photo-1568605114967-8130f3a36994',
            duration_seconds=5.0,
            camera_motion=CameraMotion.ZOOM_IN,
            model=VideoModel.FAST_SVD_LCM  # Fast model for testing
        )
    )
    print(f'✓ Video generated: {result.video_url}')

asyncio.run(test())
"
```

---

## 🐛 Troubleshooting

### Backend Issues

#### "Module not found" errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -e ".[dev]"
```

#### Database connection errors

**If using Supabase:**
```bash
# Check connection string format
# Should start with: postgresql+asyncpg://postgres.[ref]@aws-0-[region].pooler.supabase.com:6543

# Verify in Supabase Dashboard → Settings → Database
# Make sure you're using Connection Pooling (port 6543), not Direct Connection (port 5432)

# Test connection
cd backend
source venv/bin/activate
python -c "
from app.database import engine
import asyncio
async def test():
    try:
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        print('✓ Database connection OK')
    except Exception as e:
        print(f'✗ Database error: {e}')
asyncio.run(test())
"
```

**If using local PostgreSQL:**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
# Should be: postgresql+asyncpg://postgres:postgres@localhost:5432/reelestate

# Test connection manually
psql -U postgres -d reelestate
```

#### Redis connection errors
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Start Redis if not running
redis-server
# Or: brew services start redis
```

### Frontend Issues

#### "Module not found" errors
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Port 3000 already in use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9  # macOS/Linux
# Or change port in package.json scripts
```

#### TypeScript errors
```bash
# Check for type errors
npm run build

# If errors persist, try:
rm -rf .next
npm run dev
```

### Worker Issues

#### Celery worker not starting
```bash
# Check Redis connection
redis-cli ping

# Check Celery can import tasks
celery -A app.workers.celery_app inspect registered

# Check for import errors
python -c "from app.workers.tasks import render_video"
```

#### Tasks stuck in "PENDING"
```bash
# Check worker is running
celery -A app.workers.celery_app inspect active

# Check Redis is accessible
redis-cli ping
```

### fal.ai Issues

#### "Invalid API key" error
```bash
# Verify FAL_KEY in .env
cat backend/.env | grep FAL_KEY

# Test fal.ai connection
python -c "
import os
os.environ['FAL_KEY'] = 'your-key-here'
import fal_client
print('✓ fal.ai client initialized')
"
```

---

## 📊 Service Status Checklist

Use this checklist to verify everything is running:

- [ ] PostgreSQL is running and accessible
- [ ] Redis is running and accessible
- [ ] Backend API starts without errors (port 8000)
- [ ] Frontend starts without errors (port 3000)
- [ ] Celery worker starts without errors
- [ ] Database migrations applied successfully
- [ ] API health check returns 200 OK
- [ ] Frontend loads at http://localhost:3000
- [ ] API docs load at http://localhost:8000/api/docs
- [ ] Can create a user account
- [ ] Can create a project
- [ ] Video generation task can be queued

---

## 🎯 Next Steps

Once everything is running:

1. **Create your first user account**
   - Go to http://localhost:3000/signup
   - Register with email/password

2. **Set up your brand kit**
   - Upload logo
   - Choose colors
   - Add agent info

3. **Create your first project**
   - Go to Dashboard → New Project
   - Choose "Listing Tour Video"
   - Upload property photos
   - Generate script
   - Render video

4. **Test video generation**
   - Use the test script above
   - Or create a project and render it

---

## 📚 Additional Resources

- **Backend API Docs**: http://localhost:8000/api/docs
- **Frontend Dev Tools**: React DevTools, Redux DevTools
- **Database Admin**: pgAdmin or DBeaver
- **Redis GUI**: RedisInsight or Redis Commander

---

## 🆘 Need Help?

If you encounter issues:

1. Check the logs:
   - Backend: Terminal 1 output
   - Worker: Terminal 2 output
   - Frontend: Terminal 3 output

2. Verify all environment variables are set correctly

3. Check that all services are running:
   ```bash
   # Check ports
   lsof -i :8000  # Backend
   lsof -i :3000  # Frontend
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

4. Review the troubleshooting section above

---

## ✅ Success Indicators

You'll know everything is working when:

- ✅ All 4 terminals show no errors
- ✅ http://localhost:3000 shows the landing page
- ✅ http://localhost:8000/api/docs shows API documentation
- ✅ You can register a new user
- ✅ You can create a project
- ✅ Video generation tasks complete successfully

Happy coding! 🚀

