# Quick Start Guide - ReelEstate Studio

This is a condensed version. For detailed instructions, see [SETUP.md](./SETUP.md).

---

## ⚡ 5-Minute Setup

### 1. Prerequisites Check

```bash
node --version    # Need 20+
python3 --version # Need 3.11+
```

### 2. Create Supabase Project (Recommended)

1. Go to https://supabase.com
2. Create new project
3. Get connection string from Settings → Database → Connection Pooling
4. Copy the URI (replace `postgresql://` with `postgresql+asyncpg://`)

### 3. Start Redis

```bash
# Using Docker (easiest)
docker-compose up -d redis

# Or use Upstash Redis Cloud (free): https://upstash.com
```

### 4. Run Setup Script

```bash
./scripts/setup.sh
```

This will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Create .env files
- ✅ Run database migrations

### 5. Add Configuration

Edit `backend/.env`:
```env
# Database (from Supabase - Step 2)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
OPENAI_API_KEY=sk-...
FAL_KEY=...
ELEVENLABS_API_KEY=...

# Storage (use Supabase Storage or AWS S3)
SUPABASE_STORAGE_BUCKET=reelestate-media
# OR
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-secret-here
```

### 6. Start Services

**Option A: Automated (recommended)**
```bash
./scripts/start-dev.sh
```

**Option B: Manual (4 terminals)**

Terminal 1 - Backend:
```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

Terminal 2 - Worker:
```bash
cd backend && source venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info
```

Terminal 3 - Frontend:
```bash
cd frontend && npm run dev
```

### 7. Verify

- ✅ http://localhost:3000 - Frontend loads
- ✅ http://localhost:8000/health - Backend responds
- ✅ http://localhost:8000/api/docs - API docs load

---

## 🎯 First Steps

1. **Create Account**: http://localhost:3000/signup
2. **Setup Brand Kit**: Upload logo, choose colors
3. **Create Project**: Dashboard → New Project
4. **Upload Photos**: Add 5-10 property photos
5. **Generate Script**: Let AI create the script
6. **Render Video**: Generate your first video!

---

## 🛑 Stop Services

```bash
./scripts/stop-dev.sh
```

Or manually:
- Press `Ctrl+C` in each terminal
- Or kill processes: `lsof -ti:8000,3000 | xargs kill`

---

## 🐛 Common Issues

**Port already in use?**
```bash
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

**Database connection error?**
```bash
# If using Supabase:
# - Check connection string uses port 6543 (pooling)
# - Verify format: postgresql+asyncpg://postgres.[ref]@...
# - Check Supabase project is active

# If using local PostgreSQL:
pg_isready
docker-compose up -d postgres
```

**Module not found?**
```bash
# Backend
cd backend && source venv/bin/activate && pip install -e ".[dev]"

# Frontend
cd frontend && rm -rf node_modules && npm install
```

---

## 📚 Next Steps

- Read [SETUP.md](./SETUP.md) for detailed instructions
- Check [docs/](./docs/) for architecture and API docs
- Review [README.md](./README.md) for project overview

---

## 🆘 Need Help?

1. Check logs: `tail -f logs/*.log`
2. Verify environment variables are set
3. Ensure all services are running
4. Review troubleshooting in [SETUP.md](./SETUP.md)

