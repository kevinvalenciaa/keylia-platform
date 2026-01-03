# Listing Tour Video Feature - Setup & Testing Guide

## Prerequisites

Before testing, ensure you have:
- Docker and Docker Compose installed (for Redis and PostgreSQL)
- Python 3.11+ with pip
- Node.js 18+ with npm/pnpm
- FFmpeg installed on your system

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

---

## Step 1: Configure Environment Variables

### Backend (.env)

Create/update `backend/.env` with the following **required** API keys:

```bash
# Copy the example file
cp backend/env.example.txt backend/.env
```

Then edit `backend/.env` and add your actual API keys:

```env
# === REQUIRED FOR TOUR VIDEO ===

# OpenAI - For script generation
OPENAI_API_KEY=sk-your-openai-api-key

# ElevenLabs - For voiceover generation
# Get key from: https://elevenlabs.io/api
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# fal.ai - For video generation (Kling model)
# Get key from: https://fal.ai/dashboard/keys
FAL_KEY=your-fal-api-key

# AWS S3 - For storing generated videos
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_BUCKET_URL=https://your-bucket-name.s3.us-east-1.amazonaws.com

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reelestate

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_SECRET_KEY=your-secret-key-for-jwt
```

### Frontend (.env.local)

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

---

## Step 2: Start Infrastructure Services

### Option A: Using Docker Compose (Recommended)

```bash
cd /Users/kevinvalencia/keylia-platform
docker-compose up -d postgres redis
```

### Option B: Manual Start

**PostgreSQL:**
```bash
# If using local PostgreSQL
brew services start postgresql@15
# or
pg_ctl -D /usr/local/var/postgres start
```

**Redis:**
```bash
# Start Redis
redis-server --daemonize yes
# or
brew services start redis
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should output: PONG
```

---

## Step 3: Set Up the Database

```bash
cd /Users/kevinvalencia/keylia-platform/backend

# Create virtual environment (if not already)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Run database migrations
alembic upgrade head
```

---

## Step 4: Start Backend Services

You need **3 terminals** for the backend:

### Terminal 1: FastAPI Backend
```bash
cd /Users/kevinvalencia/keylia-platform/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Celery Worker
```bash
cd /Users/kevinvalencia/keylia-platform/backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --queues=video,ai,graphics
```

### Terminal 3: (Optional) Celery Flower for Monitoring
```bash
cd /Users/kevinvalencia/keylia-platform/backend
source venv/bin/activate
pip install flower
celery -A app.workers.celery_app flower --port=5555
# Access at http://localhost:5555
```

---

## Step 5: Start Frontend

```bash
cd /Users/kevinvalencia/keylia-platform/frontend
npm install  # or pnpm install
npm run dev
```

Frontend will be available at: http://localhost:3000

---

## Step 6: End-to-End Testing

### 6.1 Create a Test User

1. Open http://localhost:3000
2. Register a new account
3. Log in

### 6.2 Create a Test Listing with Photos

1. Navigate to **Listings** → **New Listing**
2. Fill in property details:
   - Address: 123 Test Street
   - City: Los Angeles
   - State: CA
   - Price: $1,500,000
   - Bedrooms: 4
   - Bathrooms: 3
   - Sqft: 2,500

3. **Upload 5-10 photos** (important - you need photos for the video!)
4. Save the listing

### 6.3 Generate a Tour Video

1. Open the listing you just created
2. Find the **"Tour Video"** card on the left sidebar
3. Click **"Generate Tour Video"**
4. Configure options:
   - **Duration:** 30 seconds (recommended for testing)
   - **Voice:** Select a voice (Rachel is default)
   - **Style:** Modern
   - **Pace:** Moderate
5. Click **"Generate Tour Video"**

### 6.4 Monitor Progress

You'll be redirected to the progress page showing:
- Script generation (5-15 seconds)
- Voiceover generation (10-30 seconds)
- Video clip generation (60-180 seconds per scene)
- Composition (30-60 seconds)
- Upload (10-30 seconds)

**Total estimated time: 2-5 minutes for 30s video**

### 6.5 Verify Result

Once complete:
1. Video player should appear with playback controls
2. **Test playback** - video should play with audio
3. **Test download** - download button should work
4. **Copy caption** - generated caption should copy to clipboard
5. Check hashtags are displayed

---

## Step 7: Verify API Endpoints Directly

### Test with curl:

**Get voices:**
```bash
curl -X GET http://localhost:8000/api/v1/tour-videos/voices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Generate video (replace with actual IDs):**
```bash
curl -X POST http://localhost:8000/api/v1/tour-videos/from-listing/LISTING_UUID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_seconds": 15,
    "voice_settings": {"gender": "female", "style": "professional"},
    "style_settings": {"tone": "modern", "pace": "moderate"}
  }'
```

**Check progress:**
```bash
curl -X GET http://localhost:8000/api/v1/tour-videos/PROJECT_UUID/progress \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Step 8: Monitor Celery Tasks

### View active tasks:
```bash
celery -A app.workers.celery_app inspect active
```

### View registered tasks:
```bash
celery -A app.workers.celery_app inspect registered
```

### Check task status in Redis:
```bash
redis-cli
> KEYS celery-task-meta-*
```

---

## Troubleshooting

### Issue: "No photos found for this listing"
- **Cause:** Photos weren't uploaded or aren't associated with the listing
- **Fix:** Re-upload photos to the listing via Supabase storage or the listing edit page

### Issue: Celery worker not processing tasks
- **Cause:** Worker not started or wrong queue
- **Fix:** Start worker with all queues:
  ```bash
  celery -A app.workers.celery_app worker --loglevel=info --queues=video,ai,graphics
  ```

### Issue: FFmpeg errors during composition
- **Cause:** FFmpeg not installed or not in PATH
- **Fix:** Install FFmpeg and ensure it's accessible:
  ```bash
  which ffmpeg  # Should output path
  ```

### Issue: ElevenLabs API errors
- **Cause:** Invalid API key or rate limiting
- **Fix:**
  - Verify ELEVENLABS_API_KEY is set correctly
  - Check your ElevenLabs quota/credits

### Issue: fal.ai video generation fails
- **Cause:** Invalid FAL_KEY or model unavailable
- **Fix:**
  - Verify FAL_KEY is set
  - Check fal.ai dashboard for status

### Issue: S3 upload fails
- **Cause:** Invalid AWS credentials or bucket permissions
- **Fix:**
  - Verify AWS credentials
  - Ensure bucket has proper CORS and public access settings

---

## Production Checklist

Before deploying to production:

- [ ] All API keys are production keys (not test/sandbox)
- [ ] S3 bucket has proper CORS configuration
- [ ] Redis is running on a managed service (not localhost)
- [ ] Celery workers are running with proper concurrency
- [ ] Database migrations are applied
- [ ] Environment variables are set in production environment
- [ ] FFmpeg is installed on worker servers
- [ ] SSL/HTTPS is configured
- [ ] Rate limiting is configured for API endpoints
- [ ] Error monitoring (Sentry) is set up
- [ ] Log aggregation is configured

---

## API Cost Estimates (Per Video)

| Service | 30s Video | 60s Video |
|---------|-----------|-----------|
| OpenAI GPT-4 | ~$0.05 | ~$0.08 |
| ElevenLabs | ~$0.15 | ~$0.30 |
| fal.ai Kling | ~$0.50-1.00 | ~$1.00-2.00 |
| **Total** | ~$0.70-1.20 | ~$1.40-2.40 |

*Costs are approximate and may vary based on usage and pricing changes.*
