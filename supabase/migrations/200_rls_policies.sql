-- =============================================================================
-- RLS Policies for Backend Schema
-- =============================================================================
-- Run this in Supabase SQL Editor after the Alembic migrations
-- These policies allow the frontend Supabase client to query backend tables
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_kits ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- USERS TABLE POLICIES
-- =============================================================================
-- Users can read their own record (matched by supabase_id)
CREATE POLICY "Users can view own user record" ON users
  FOR SELECT USING (supabase_id = auth.uid()::text);

-- Users can update their own record
CREATE POLICY "Users can update own user record" ON users
  FOR UPDATE USING (supabase_id = auth.uid()::text);

-- =============================================================================
-- ORGANIZATIONS TABLE POLICIES
-- =============================================================================
-- Users can view organizations they're members of
CREATE POLICY "Users can view their organizations" ON organizations
  FOR SELECT USING (
    id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- Users can create organizations (they become the owner)
CREATE POLICY "Users can create organizations" ON organizations
  FOR INSERT WITH CHECK (
    owner_id IN (
      SELECT id FROM users WHERE supabase_id = auth.uid()::text
    )
  );

-- Owners can update their organizations
CREATE POLICY "Owners can update organizations" ON organizations
  FOR UPDATE USING (
    owner_id IN (
      SELECT id FROM users WHERE supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- ORGANIZATION MEMBERS TABLE POLICIES
-- =============================================================================
-- Users can view their own membership OR memberships in orgs they own
CREATE POLICY "Users can view org memberships" ON organization_members
  FOR SELECT USING (
    -- User can see their own membership record
    user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text)
    OR
    -- User can see all memberships in organizations they own
    organization_id IN (
      SELECT o.id FROM organizations o
      JOIN users u ON o.owner_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- Org owners/admins can manage memberships
CREATE POLICY "Admins can manage memberships" ON organization_members
  FOR ALL USING (
    organization_id IN (
      SELECT o.id FROM organizations o
      JOIN users u ON o.owner_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- PROPERTY LISTINGS TABLE POLICIES
-- =============================================================================
-- Users can view listings in their organizations
CREATE POLICY "Users can view org listings" ON property_listings
  FOR SELECT USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- Users can create listings in their organizations
CREATE POLICY "Users can create org listings" ON property_listings
  FOR INSERT WITH CHECK (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- Users can update listings in their organizations
CREATE POLICY "Users can update org listings" ON property_listings
  FOR UPDATE USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- Users can delete listings in their organizations
CREATE POLICY "Users can delete org listings" ON property_listings
  FOR DELETE USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- BRAND KITS TABLE POLICIES
-- =============================================================================
CREATE POLICY "Users can view org brand kits" ON brand_kits
  FOR SELECT USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can manage org brand kits" ON brand_kits
  FOR ALL USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- PROJECTS TABLE POLICIES
-- =============================================================================
CREATE POLICY "Users can view org projects" ON projects
  FOR SELECT USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can create org projects" ON projects
  FOR INSERT WITH CHECK (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can update org projects" ON projects
  FOR UPDATE USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can delete org projects" ON projects
  FOR DELETE USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- RENDER JOBS TABLE POLICIES
-- =============================================================================
CREATE POLICY "Users can view org render jobs" ON render_jobs
  FOR SELECT USING (
    project_id IN (
      SELECT p.id FROM projects p
      WHERE p.organization_id IN (
        SELECT om.organization_id FROM organization_members om
        JOIN users u ON om.user_id = u.id
        WHERE u.supabase_id = auth.uid()::text
      )
    )
  );

-- =============================================================================
-- MEDIA ASSETS TABLE POLICIES
-- =============================================================================
CREATE POLICY "Users can view org media assets" ON media_assets
  FOR SELECT USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can manage org media assets" ON media_assets
  FOR ALL USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- SUBSCRIPTIONS TABLE POLICIES
-- =============================================================================
CREATE POLICY "Users can view org subscriptions" ON subscriptions
  FOR SELECT USING (
    organization_id IN (
      SELECT om.organization_id FROM organization_members om
      JOIN users u ON om.user_id = u.id
      WHERE u.supabase_id = auth.uid()::text
    )
  );

-- =============================================================================
-- AUTO-CREATE USER AND ORGANIZATION ON SIGNUP
-- =============================================================================
-- This trigger creates a user and personal organization when someone signs up
CREATE OR REPLACE FUNCTION public.handle_new_supabase_user()
RETURNS TRIGGER AS $$
DECLARE
  new_user_id UUID;
  new_org_id UUID;
  user_slug TEXT;
BEGIN
  -- Generate UUIDs
  new_user_id := gen_random_uuid();
  new_org_id := gen_random_uuid();

  -- Create slug from email
  user_slug := lower(regexp_replace(split_part(NEW.email, '@', 1), '[^a-z0-9]', '-', 'g'));
  user_slug := user_slug || '-' || substr(new_org_id::text, 1, 8);

  -- Create user in users table
  INSERT INTO public.users (id, email, full_name, supabase_id, email_verified, is_active)
  VALUES (
    new_user_id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    NEW.id::text,
    COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
    true
  );

  -- Create personal organization
  INSERT INTO public.organizations (id, name, slug, owner_id)
  VALUES (
    new_org_id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)) || '''s Workspace',
    user_slug,
    new_user_id
  );

  -- Add user as owner of organization
  INSERT INTO public.organization_members (id, organization_id, user_id, role)
  VALUES (
    gen_random_uuid(),
    new_org_id,
    new_user_id,
    'owner'
  );

  -- Create trial subscription
  INSERT INTO public.subscriptions (id, organization_id, plan_name, status, trial_end, video_renders_limit, video_renders_used, storage_limit_gb, storage_used_bytes)
  VALUES (
    gen_random_uuid(),
    new_org_id,
    'trial',
    'trial',
    NOW() + INTERVAL '14 days',
    10,
    0,
    5,
    0
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if any
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_supabase_user();
