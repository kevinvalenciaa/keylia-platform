# Supabase Setup Guide

This guide explains how to set up and use Supabase as your database and storage provider for ReelEstate Studio.

---

## Why Supabase?

- ✅ **Free tier** - Perfect for development and small projects
- ✅ **PostgreSQL** - Full-featured relational database
- ✅ **Built-in storage** - Can replace AWS S3
- ✅ **Real-time** - Built-in subscriptions
- ✅ **Authentication** - Can replace custom JWT (optional)
- ✅ **No local setup** - No need to run PostgreSQL locally
- ✅ **Easy migrations** - Works with Alembic

---

## Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Click **"Start your project"** or **"Sign in"**
3. Click **"New Project"**
4. Fill in:
   - **Organization**: Select or create one
   - **Name**: `reelestate-studio` (or your choice)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free tier is fine for development
5. Click **"Create new project"**
6. Wait ~2 minutes for project to be created

---

## Step 2: Get Database Connection String

1. In your Supabase Dashboard, go to **Settings** (gear icon) → **Database**
2. Scroll to **Connection String** section
3. Click on **Connection Pooling** tab
4. Select **Session mode** (recommended for most apps)
5. Copy the **URI** connection string
   - It looks like: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
6. **Important**: Replace `postgresql://` with `postgresql+asyncpg://` for async support
   - Final format: `postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

---

## Step 3: Add to Environment Variables

Add to `backend/.env`:

```env
# Database connection (from Step 2)
DATABASE_URL=postgresql+asyncpg://postgres.[your-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Supabase API (optional - for storage/auth features)
SUPABASE_URL=https://[your-project-ref].supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here
```

To get the API keys:
1. Go to **Settings** → **API**
2. Copy **Project URL** → `SUPABASE_URL`
3. Copy **anon public** key → `SUPABASE_KEY`
4. Copy **service_role** key → `SUPABASE_SERVICE_KEY` (keep this secret!)

---

## Step 4: Run Migrations

```bash
cd backend
source venv/bin/activate

# Run migrations
alembic upgrade head
```

This will create all tables in your Supabase database.

---

## Step 5: Verify Connection

```bash
cd backend
source venv/bin/activate
python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT version()')
        print('✓ Connected to Supabase PostgreSQL')
        print(f'  {result.scalar()[:50]}...')
asyncio.run(test())
"
```

---

## Optional: Use Supabase Storage

Instead of AWS S3, you can use Supabase Storage (free tier includes 1GB):

### Setup Storage Bucket

1. In Supabase Dashboard → **Storage**
2. Click **"New bucket"**
3. Name: `reelestate-media`
4. Make it **Public** (for CDN access) or **Private** (with policies)
5. Click **"Create bucket"**

### Update Code to Use Supabase Storage

You'll need to update the storage service to use Supabase Storage API instead of S3. The Supabase Python client makes this easy:

```python
from supabase import create_client, Client

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

# Upload file
response = supabase.storage.from_("reelestate-media").upload(
    file_path=file_path,
    file=file_data,
    file_options={"content-type": "image/jpeg"}
)

# Get public URL
url = supabase.storage.from_("reelestate-media").get_public_url(file_path)
```

---

## Optional: Use Supabase Auth

Supabase provides built-in authentication that can replace custom JWT:

- Email/password
- OAuth (Google, GitHub, etc.)
- Magic links
- Phone auth

This is optional - the current setup uses custom JWT which works fine.

---

## Database Management

### View Data in Supabase

1. Go to **Table Editor** in Supabase Dashboard
2. See all your tables and data
3. Edit data directly in the UI

### Run SQL Queries

1. Go to **SQL Editor** in Supabase Dashboard
2. Write and run SQL queries
3. Save queries for later

### Monitor Performance

1. Go to **Database** → **Reports**
2. See query performance
3. Monitor connection pool usage

---

## Connection Pooling

Supabase uses **PgBouncer** for connection pooling. Always use:

- **Port 6543** (Connection Pooling) - Recommended
- **Port 5432** (Direct Connection) - Only for migrations/admin

The connection string from Step 2 already uses port 6543.

---

## Free Tier Limits

Supabase free tier includes:
- ✅ 500 MB database
- ✅ 1 GB file storage
- ✅ 2 GB bandwidth
- ✅ 50,000 monthly active users
- ✅ Unlimited API requests

This is perfect for development and small projects!

---

## Production Considerations

For production:
1. Upgrade to Pro plan ($25/month) for:
   - More storage (8 GB database, 100 GB files)
   - Better performance
   - Daily backups
   - Point-in-time recovery

2. Set up:
   - Database backups
   - Connection pooling limits
   - Row Level Security (RLS) policies
   - API rate limiting

---

## Troubleshooting

### Connection Timeout

- Check you're using port **6543** (pooling), not 5432
- Verify connection string format is correct
- Check Supabase project is active (not paused)

### Migration Errors

- Make sure you're using the **service_role** key for migrations
- Check database password is correct
- Verify connection string uses `postgresql+asyncpg://`

### Storage Upload Fails

- Check bucket exists and is accessible
- Verify `SUPABASE_SERVICE_KEY` is set (not anon key)
- Check file size limits (free tier: 50 MB per file)

---

## Resources

- **Supabase Docs**: https://supabase.com/docs
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Connection Pooling**: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
- **Storage Guide**: https://supabase.com/docs/guides/storage

---

## Next Steps

1. ✅ Database connected
2. ✅ Migrations run
3. ✅ Storage bucket created (optional)
4. ✅ Ready to develop!

Continue with the main [SETUP.md](../SETUP.md) guide for the rest of the setup.

