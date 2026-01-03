# Supabase Setup Guide for ReelEstate Studio

This guide walks you through setting up Supabase as the database for ReelEstate Studio.

## Prerequisites

1. A Supabase account ([supabase.com](https://supabase.com))
2. A new Supabase project created

## Step-by-Step Setup

### Step 1: Create a New Supabase Project

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Click "New Project"
3. Fill in:
   - **Name**: `reelestate-studio`
   - **Database Password**: (save this securely!)
   - **Region**: Choose closest to your users
4. Click "Create new project"
5. Wait for the project to initialize (~2 minutes)

### Step 2: Get Your Connection Details

From your project dashboard, go to **Settings > Database**:

1. **Connection String (for backend)**:
   ```
   postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```

2. **Direct Connection** (for migrations):
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```

From **Settings > API**:
- `SUPABASE_URL`: Your project URL
- `SUPABASE_ANON_KEY`: The `anon` public key
- `SUPABASE_SERVICE_KEY`: The `service_role` key (keep secret!)

### Step 3: Run Database Migrations

#### Option A: Via Supabase SQL Editor (Recommended)

1. Go to **SQL Editor** in your Supabase dashboard
2. Click **New Query**
3. Copy the entire contents of `migrations/001_initial_schema.sql`
4. Click **Run** (or press Cmd/Ctrl + Enter)
5. Verify: You should see "Success. No rows returned"
6. Repeat for `migrations/002_storage_buckets.sql`

#### Option B: Via Command Line

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref YOUR_PROJECT_REF

# Push migrations
supabase db push
```

### Step 4: Create Storage Buckets

Go to **Storage** in your Supabase dashboard:

1. **Create `media-assets` bucket**:
   - Click "New Bucket"
   - Name: `media-assets`
   - Public: ❌ OFF (private)
   - File size limit: `104857600` (100MB)
   - Allowed MIME types: `image/*,video/*,audio/*`

2. **Create `brand-assets` bucket**:
   - Name: `brand-assets`
   - Public: ✅ ON (public for logos)
   - File size limit: `10485760` (10MB)
   - Allowed MIME types: `image/*`

3. **Create `rendered-videos` bucket**:
   - Name: `rendered-videos`
   - Public: ❌ OFF (private)
   - File size limit: `524288000` (500MB)
   - Allowed MIME types: `video/*`

### Step 5: Configure Authentication

Go to **Authentication > Providers**:

1. **Email** (enabled by default):
   - Enable "Confirm email"
   - Set site URL: `http://localhost:3000` (dev) or your domain

2. **Google OAuth** (optional):
   - Enable Google provider
   - Add OAuth credentials from Google Cloud Console
   - Redirect URL: `https://[PROJECT-REF].supabase.co/auth/v1/callback`

### Step 6: Configure Environment Variables

#### Backend (.env)

```bash
# Database - Use the pooler connection for better performance
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres

# Supabase (optional - for direct Supabase features)
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_KEY=[ANON_KEY]
SUPABASE_SERVICE_KEY=[SERVICE_ROLE_KEY]
```

#### Frontend (.env.local)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[ANON_KEY]
```

### Step 7: Verify Setup

Run this query in SQL Editor to verify tables were created:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Expected tables:
- `audit_logs`
- `brand_kits`
- `media_assets`
- `organization_members`
- `organizations`
- `projects`
- `property_listings`
- `published_content`
- `render_jobs`
- `scenes`
- `social_accounts`
- `subscriptions`
- `usage_records`
- `users`

### Step 8: Test RLS Policies

```sql
-- This should return empty (no auth context in SQL Editor)
SELECT * FROM projects;

-- This should work (service role bypass)
SET ROLE service_role;
SELECT COUNT(*) FROM users;
```

## Production Checklist

### Security

- [ ] Strong database password (32+ characters)
- [ ] `SUPABASE_SERVICE_KEY` only on backend, never exposed to client
- [ ] RLS policies tested for all tables
- [ ] API rate limiting configured
- [ ] CORS configured for your domains only

### Performance

- [ ] Connection pooling enabled (use `pooler.supabase.com`)
- [ ] Appropriate indexes created (done in migration)
- [ ] Query performance monitored via Dashboard > Database > Query Performance

### Monitoring

- [ ] Enable database webhooks for critical events
- [ ] Set up error alerting
- [ ] Configure log retention

### Backup

- [ ] Point-in-time recovery enabled (Pro plan)
- [ ] Regular backups scheduled
- [ ] Backup restoration tested

## Useful Queries

### Check Organization Usage

```sql
SELECT * FROM organization_usage_summary;
```

### Check Active Subscriptions

```sql
SELECT 
    o.name,
    s.plan_name,
    s.status,
    s.video_renders_used,
    s.video_renders_limit,
    s.current_period_end
FROM subscriptions s
JOIN organizations o ON o.id = s.organization_id
WHERE s.status = 'active';
```

### Find Failed Render Jobs

```sql
SELECT 
    r.id,
    p.title as project_title,
    r.error_message,
    r.created_at
FROM render_jobs r
JOIN projects p ON p.id = r.project_id
WHERE r.status = 'failed'
ORDER BY r.created_at DESC
LIMIT 20;
```

### Storage Usage by Organization

```sql
SELECT 
    o.name,
    get_org_storage_usage(o.id).*
FROM organizations o;
```

## Troubleshooting

### "permission denied for table X"

RLS is blocking access. Ensure:
1. User is authenticated
2. User is a member of the organization
3. Check the specific RLS policy

### "connection refused"

1. Check if using correct connection string
2. Verify project is not paused (Supabase pauses inactive free projects)
3. Check IP allowlist if configured

### Slow Queries

1. Check **Dashboard > Database > Query Performance**
2. Add missing indexes
3. Use `EXPLAIN ANALYZE` to debug

## Support

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Discord](https://discord.supabase.com)
- [GitHub Issues](https://github.com/supabase/supabase/issues)

