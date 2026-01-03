# ⚡ Supabase Quick Setup

## 1️⃣ Create Project
- Go to [supabase.com](https://supabase.com) → New Project
- Save your database password!

## 2️⃣ Run SQL Migrations

Go to **SQL Editor** → **New Query** → Paste & Run each file:

```
supabase/migrations/001_initial_schema.sql  ← Run first (creates tables)
supabase/migrations/002_storage_buckets.sql ← Run second (storage + audit)
supabase/migrations/003_seed_data.sql       ← Optional (demo data)
```

## 3️⃣ Create Storage Buckets

Go to **Storage** → **New Bucket**:

| Bucket | Public | Size Limit |
|--------|--------|------------|
| `media-assets` | ❌ No | 100MB |
| `brand-assets` | ✅ Yes | 10MB |
| `rendered-videos` | ❌ No | 500MB |

## 4️⃣ Get Connection String

Go to **Settings** → **Database** → Copy "Connection string":

```
postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

## 5️⃣ Update Backend .env

```bash
DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_KEY=[anon key from Settings > API]
SUPABASE_SERVICE_KEY=[service_role key from Settings > API]
```

## 6️⃣ Verify

Run in SQL Editor:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' ORDER BY table_name;
```

Should show 14 tables ✅

---

## 📋 Tables Created

| Table | Purpose |
|-------|---------|
| `users` | User accounts |
| `organizations` | Multi-tenant orgs |
| `organization_members` | Org memberships |
| `brand_kits` | Agent branding |
| `property_listings` | Property data |
| `projects` | Video/infographic projects |
| `media_assets` | Uploaded files |
| `scenes` | Video timeline |
| `render_jobs` | Video rendering queue |
| `subscriptions` | Billing plans |
| `usage_records` | Usage tracking |
| `social_accounts` | Connected platforms |
| `published_content` | Posted content |
| `audit_logs` | Change history |

## 🔐 Security Features

- ✅ Row Level Security (RLS) enabled on all tables
- ✅ Organization-scoped data isolation
- ✅ Role-based access (owner, admin, member, viewer)
- ✅ Storage bucket policies
- ✅ Audit logging on sensitive tables

## 🆘 Troubleshooting

**"permission denied"** → Check RLS policies, ensure user is org member

**"connection refused"** → Use pooler connection string (port 6543)

**Tables missing** → Run migration 001 first, check for SQL errors

---

Full docs: `supabase/README.md`

