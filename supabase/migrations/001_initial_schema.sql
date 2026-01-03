-- =============================================================================
-- Keylia - Initial Database Schema
-- =============================================================================
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- This creates all tables, indexes, RLS policies, and triggers
-- =============================================================================

-- ============================================================================
-- STEP 1: Enable Required Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Password hashing (if needed)

-- ============================================================================
-- STEP 2: Create Custom Types (Enums)
-- ============================================================================

-- Project types
DO $$ BEGIN
    CREATE TYPE project_type AS ENUM ('listing_tour', 'promo_video', 'infographic');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Project status
DO $$ BEGIN
    CREATE TYPE project_status AS ENUM ('draft', 'script_pending', 'script_ready', 'rendering', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Render status
DO $$ BEGIN
    CREATE TYPE render_status AS ENUM ('queued', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Subscription status
DO $$ BEGIN
    CREATE TYPE subscription_status AS ENUM ('active', 'trialing', 'past_due', 'cancelled', 'unpaid');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Media type
DO $$ BEGIN
    CREATE TYPE media_type AS ENUM ('image', 'video', 'audio', 'voiceover', 'music', 'logo', 'headshot');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- STEP 3: Create Tables
-- ============================================================================

-- -----------------------------------------------------------------------------
-- Users Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    phone VARCHAR(50),
    google_id VARCHAR(255) UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- -----------------------------------------------------------------------------
-- Organizations Table (Multi-tenancy)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    stripe_customer_id VARCHAR(255),
    logo_url TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for organizations
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_owner ON organizations(owner_id);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe ON organizations(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Organization Members Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    permissions JSONB DEFAULT '{}',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    invited_by UUID REFERENCES users(id),
    
    -- Prevent duplicate memberships
    UNIQUE(organization_id, user_id)
);

-- Indexes for organization_members
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(organization_id, role);

-- -----------------------------------------------------------------------------
-- Brand Kits Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS brand_kits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Agent information
    agent_name VARCHAR(255),
    agent_title VARCHAR(255),
    agent_email VARCHAR(255),
    agent_phone VARCHAR(50),
    brokerage_name VARCHAR(255),
    license_number VARCHAR(100),
    
    -- Visual assets
    logo_url TEXT,
    logo_light_url TEXT,
    headshot_url TEXT,
    watermark_url TEXT,
    
    -- Colors (hex format)
    primary_color VARCHAR(7) DEFAULT '#2563eb',
    secondary_color VARCHAR(7) DEFAULT '#1e40af',
    accent_color VARCHAR(7) DEFAULT '#f59e0b',
    background_color VARCHAR(7) DEFAULT '#ffffff',
    text_color VARCHAR(7) DEFAULT '#1f2937',
    
    -- Typography
    heading_font VARCHAR(100) DEFAULT 'Inter',
    body_font VARCHAR(100) DEFAULT 'Inter',
    
    -- Social links
    social_links JSONB DEFAULT '{}',
    
    -- Compliance
    compliance_text TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for brand_kits
CREATE INDEX IF NOT EXISTS idx_brand_kits_org ON brand_kits(organization_id);
CREATE INDEX IF NOT EXISTS idx_brand_kits_default ON brand_kits(organization_id, is_default) WHERE is_default = TRUE;

-- -----------------------------------------------------------------------------
-- Property Listings Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS property_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Address
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    neighborhood VARCHAR(100),
    
    -- Geocoding
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    
    -- Property details
    listing_price DECIMAL(12, 2),
    original_price DECIMAL(12, 2),
    bedrooms SMALLINT CHECK (bedrooms >= 0),
    bathrooms DECIMAL(3, 1) CHECK (bathrooms >= 0),
    half_baths SMALLINT DEFAULT 0,
    square_feet INTEGER CHECK (square_feet > 0),
    lot_size VARCHAR(50),
    lot_size_sqft INTEGER,
    year_built SMALLINT,
    stories SMALLINT,
    garage_spaces SMALLINT,
    property_type VARCHAR(50),
    
    -- Status
    listing_status VARCHAR(50) DEFAULT 'for_sale' CHECK (listing_status IN ('for_sale', 'pending', 'sold', 'off_market', 'coming_soon', 'for_rent', 'rented')),
    days_on_market INTEGER DEFAULT 0,
    
    -- Features (stored as array)
    features TEXT[] DEFAULT '{}',
    amenities TEXT[] DEFAULT '{}',
    
    -- MLS
    mls_number VARCHAR(50),
    mls_source VARCHAR(100),
    
    -- Marketing
    headline VARCHAR(255),
    description TEXT,
    target_audience VARCHAR(255),
    positioning_notes TEXT,
    virtual_tour_url TEXT,
    
    -- Open house
    open_house_date DATE,
    open_house_start TIME,
    open_house_end TIME,
    open_house_notes TEXT,
    
    -- Metadata
    imported_from VARCHAR(100),
    external_id VARCHAR(255),
    raw_data JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for property_listings
CREATE INDEX IF NOT EXISTS idx_properties_org ON property_listings(organization_id);
CREATE INDEX IF NOT EXISTS idx_properties_status ON property_listings(listing_status);
CREATE INDEX IF NOT EXISTS idx_properties_mls ON property_listings(mls_number) WHERE mls_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_properties_city_state ON property_listings(city, state);
CREATE INDEX IF NOT EXISTS idx_properties_price ON property_listings(listing_price) WHERE listing_price IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_properties_created ON property_listings(created_at DESC);

-- Full-text search index for properties
CREATE INDEX IF NOT EXISTS idx_properties_search ON property_listings 
    USING GIN (to_tsvector('english', COALESCE(address_line1, '') || ' ' || COALESCE(city, '') || ' ' || COALESCE(neighborhood, '')));

-- -----------------------------------------------------------------------------
-- Projects Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    property_id UUID REFERENCES property_listings(id) ON DELETE SET NULL,
    brand_kit_id UUID REFERENCES brand_kits(id) ON DELETE SET NULL,
    
    -- Basic info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('listing_tour', 'promo_video', 'infographic')),
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'script_pending', 'script_ready', 'rendering', 'completed', 'failed', 'archived')),
    
    -- Settings (flexible JSONB)
    style_settings JSONB DEFAULT '{
        "tone": "modern",
        "pace": "moderate",
        "music_vibe": "cinematic",
        "duration_seconds": 30,
        "platform": "instagram_reels",
        "aspect_ratio": "9:16"
    }',
    voice_settings JSONB DEFAULT '{
        "enabled": true,
        "language": "en-US",
        "gender": "female",
        "style": "friendly"
    }',
    infographic_settings JSONB DEFAULT '{
        "layout": "single_card",
        "emphasis": "feature_driven",
        "animation": "light_motion"
    }',
    
    -- AI Generated content
    generated_script JSONB,
    generated_caption TEXT,
    generated_hashtags TEXT[],
    
    -- Output
    final_video_url TEXT,
    final_thumbnail_url TEXT,
    
    -- Tracking
    render_count INTEGER DEFAULT 0,
    last_rendered_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for projects
CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(organization_id, type);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_projects_property ON projects(property_id) WHERE property_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_creator ON projects(created_by_id);

-- -----------------------------------------------------------------------------
-- Media Assets Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    uploaded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- File info
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('image', 'video', 'audio', 'voiceover', 'music', 'logo', 'headshot', 'other')),
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
    
    -- Storage
    storage_provider VARCHAR(50) DEFAULT 'supabase',
    storage_bucket VARCHAR(100),
    storage_key VARCHAR(500) NOT NULL,
    storage_url TEXT NOT NULL,
    cdn_url TEXT,
    
    -- Thumbnails
    thumbnail_url TEXT,
    thumbnail_storage_key VARCHAR(500),
    
    -- Dimensions (for images/videos)
    width INTEGER,
    height INTEGER,
    duration_seconds DECIMAL(10, 2),
    
    -- Categorization
    category VARCHAR(50),
    tags TEXT[] DEFAULT '{}',
    
    -- AI Analysis
    ai_description TEXT,
    ai_tags TEXT[] DEFAULT '{}',
    ai_quality_score DECIMAL(3, 2),
    ai_analyzed_at TIMESTAMPTZ,
    
    -- Processing
    processing_status VARCHAR(50) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,
    
    -- Metadata
    exif_data JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for media_assets
CREATE INDEX IF NOT EXISTS idx_media_org ON media_assets(organization_id);
CREATE INDEX IF NOT EXISTS idx_media_project ON media_assets(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_type ON media_assets(organization_id, file_type);
CREATE INDEX IF NOT EXISTS idx_media_category ON media_assets(organization_id, category) WHERE category IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_created ON media_assets(created_at DESC);

-- -----------------------------------------------------------------------------
-- Scenes Table (Video Timeline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    
    -- Ordering and timing
    sequence_order SMALLINT NOT NULL,
    start_time_ms INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL CHECK (duration_ms > 0),
    
    -- Content
    narration_text TEXT,
    on_screen_text VARCHAR(100),
    
    -- Visual settings
    camera_movement JSONB DEFAULT '{
        "type": "zoom_in",
        "start_position": {"x": 0.5, "y": 0.5, "scale": 1.0},
        "end_position": {"x": 0.5, "y": 0.5, "scale": 1.15},
        "easing": "ease-in-out"
    }',
    
    -- Transitions
    transition_type VARCHAR(50) DEFAULT 'crossfade' CHECK (transition_type IN ('none', 'crossfade', 'fade_black', 'slide_left', 'slide_right', 'zoom', 'wipe')),
    transition_duration_ms INTEGER DEFAULT 500,
    
    -- Overlays and effects
    overlay_settings JSONB DEFAULT '{}',
    filters JSONB DEFAULT '{}',
    
    -- AI Generation tracking
    generated_video_url TEXT,
    generation_status VARCHAR(50) DEFAULT 'pending',
    generation_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique ordering within project
    UNIQUE(project_id, sequence_order)
);

-- Indexes for scenes
CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id);
CREATE INDEX IF NOT EXISTS idx_scenes_order ON scenes(project_id, sequence_order);
CREATE INDEX IF NOT EXISTS idx_scenes_media ON scenes(media_asset_id) WHERE media_asset_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Render Jobs Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS render_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    triggered_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Type
    render_type VARCHAR(50) DEFAULT 'final' CHECK (render_type IN ('preview', 'final', 'export_variant', 'thumbnail')),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    progress_percent SMALLINT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    current_step VARCHAR(100),
    
    -- Settings used for this render
    settings JSONB DEFAULT '{}',
    
    -- Output
    output_url TEXT,
    output_file_size BIGINT,
    output_duration_seconds DECIMAL(10, 2),
    output_width INTEGER,
    output_height INTEGER,
    output_fps INTEGER,
    output_bitrate VARCHAR(50),
    
    -- Subtitles
    subtitle_url TEXT,
    subtitle_format VARCHAR(10),
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    error_code VARCHAR(50),
    retry_count SMALLINT DEFAULT 0,
    
    -- Timing
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Worker info
    worker_id VARCHAR(100),
    celery_task_id VARCHAR(255),
    
    -- Cost tracking
    credits_used INTEGER DEFAULT 0,
    processing_time_seconds INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for render_jobs
CREATE INDEX IF NOT EXISTS idx_renders_project ON render_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_renders_status ON render_jobs(status);
CREATE INDEX IF NOT EXISTS idx_renders_type_status ON render_jobs(render_type, status);
CREATE INDEX IF NOT EXISTS idx_renders_created ON render_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_renders_celery ON render_jobs(celery_task_id) WHERE celery_task_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Subscriptions Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Stripe
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    stripe_product_id VARCHAR(255),
    
    -- Plan details
    plan_name VARCHAR(50) NOT NULL CHECK (plan_name IN ('free', 'starter', 'professional', 'team', 'enterprise')),
    billing_interval VARCHAR(20) DEFAULT 'monthly' CHECK (billing_interval IN ('monthly', 'yearly')),
    
    -- Usage limits
    video_renders_limit INTEGER,
    video_renders_used INTEGER DEFAULT 0,
    ai_generations_limit INTEGER,
    ai_generations_used INTEGER DEFAULT 0,
    storage_limit_gb INTEGER,
    storage_used_bytes BIGINT DEFAULT 0,
    team_members_limit INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'trialing', 'past_due', 'cancelled', 'unpaid', 'incomplete')),
    
    -- Period
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Payment
    last_payment_at TIMESTAMPTZ,
    last_payment_amount DECIMAL(10, 2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_org ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan ON subscriptions(plan_name);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_period_end ON subscriptions(current_period_end) WHERE current_period_end IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Usage Records Table (Detailed tracking)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Usage details
    usage_type VARCHAR(50) NOT NULL CHECK (usage_type IN ('video_render', 'ai_script', 'ai_caption', 'voiceover', 'storage_upload', 'export')),
    quantity INTEGER DEFAULT 1,
    
    -- References
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    render_job_id UUID REFERENCES render_jobs(id) ON DELETE SET NULL,
    
    -- Billing
    credits_consumed INTEGER DEFAULT 0,
    billing_period VARCHAR(7), -- YYYY-MM format
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for usage_records
CREATE INDEX IF NOT EXISTS idx_usage_org ON usage_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_records(organization_id, usage_type);
CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_records(organization_id, billing_period);
CREATE INDEX IF NOT EXISTS idx_usage_recorded ON usage_records(recorded_at DESC);

-- -----------------------------------------------------------------------------
-- Social Accounts Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    connected_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Platform info
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('instagram', 'facebook', 'tiktok', 'youtube', 'linkedin', 'twitter')),
    platform_user_id VARCHAR(255),
    username VARCHAR(255),
    display_name VARCHAR(255),
    profile_url TEXT,
    profile_image_url TEXT,
    
    -- OAuth tokens (encrypted in production)
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    
    -- Permissions/scopes
    scopes TEXT[],
    
    -- Status
    is_connected BOOLEAN DEFAULT TRUE,
    connection_error TEXT,
    last_error_at TIMESTAMPTZ,
    
    -- Sync
    last_synced_at TIMESTAMPTZ,
    follower_count INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One account per platform per org
    UNIQUE(organization_id, platform, platform_user_id)
);

-- Indexes for social_accounts
CREATE INDEX IF NOT EXISTS idx_social_org ON social_accounts(organization_id);
CREATE INDEX IF NOT EXISTS idx_social_platform ON social_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_social_connected ON social_accounts(organization_id, is_connected) WHERE is_connected = TRUE;

-- -----------------------------------------------------------------------------
-- Published Content Table (Track what's been posted)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS published_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    
    -- Platform post info
    platform_post_id VARCHAR(255),
    platform_url TEXT,
    
    -- Content
    caption TEXT,
    hashtags TEXT[],
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'scheduled', 'published', 'failed', 'deleted')),
    error_message TEXT,
    
    -- Scheduling
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    
    -- Analytics (updated via webhook/sync)
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5, 2),
    last_analytics_sync TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for published_content
CREATE INDEX IF NOT EXISTS idx_published_project ON published_content(project_id);
CREATE INDEX IF NOT EXISTS idx_published_account ON published_content(social_account_id);
CREATE INDEX IF NOT EXISTS idx_published_status ON published_content(status);
CREATE INDEX IF NOT EXISTS idx_published_scheduled ON published_content(scheduled_for) WHERE scheduled_for IS NOT NULL;

-- ============================================================================
-- STEP 4: Create Updated_at Trigger Function
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 5: Apply Updated_at Triggers to All Tables
-- ============================================================================

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
        AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 6: Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_kits ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE published_content ENABLE ROW LEVEL SECURITY;

-- Helper function to get user's organization IDs
CREATE OR REPLACE FUNCTION get_user_organization_ids(user_uuid UUID)
RETURNS UUID[] AS $$
    SELECT ARRAY_AGG(organization_id)
    FROM organization_members
    WHERE user_id = user_uuid;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- -----------------------------------------------------------------------------
-- Users Policies
-- -----------------------------------------------------------------------------
-- Users can read their own profile
CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = auth.uid());

-- Users can update their own profile
CREATE POLICY users_update_own ON users
    FOR UPDATE USING (id = auth.uid());

-- Service role can do everything
CREATE POLICY users_service_all ON users
    FOR ALL USING (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Organizations Policies
-- -----------------------------------------------------------------------------
-- Members can view their organizations
CREATE POLICY organizations_select ON organizations
    FOR SELECT USING (
        id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid())
    );

-- Owners can update their organizations
CREATE POLICY organizations_update ON organizations
    FOR UPDATE USING (owner_id = auth.uid());

-- Any authenticated user can create an organization
CREATE POLICY organizations_insert ON organizations
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Service role bypass
CREATE POLICY organizations_service_all ON organizations
    FOR ALL USING (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Organization Members Policies
-- -----------------------------------------------------------------------------
-- Members can view other members in their org
CREATE POLICY org_members_select ON organization_members
    FOR SELECT USING (
        organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid())
    );

-- Owners/admins can manage members
CREATE POLICY org_members_insert ON organization_members
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM organization_members 
            WHERE user_id = auth.uid() 
            AND organization_id = organization_members.organization_id
            AND role IN ('owner', 'admin')
        )
    );

CREATE POLICY org_members_delete ON organization_members
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM organization_members om
            WHERE om.user_id = auth.uid() 
            AND om.organization_id = organization_members.organization_id
            AND om.role IN ('owner', 'admin')
        )
        OR user_id = auth.uid() -- Users can leave
    );

-- Service role bypass
CREATE POLICY org_members_service_all ON organization_members
    FOR ALL USING (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Brand Kits, Properties, Projects, Media, Scenes, Renders Policies
-- (Organization-scoped access)
-- -----------------------------------------------------------------------------

-- Brand Kits
CREATE POLICY brand_kits_select ON brand_kits
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY brand_kits_insert ON brand_kits
    FOR INSERT WITH CHECK (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY brand_kits_update ON brand_kits
    FOR UPDATE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY brand_kits_delete ON brand_kits
    FOR DELETE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY brand_kits_service_all ON brand_kits
    FOR ALL USING (auth.role() = 'service_role');

-- Property Listings
CREATE POLICY properties_select ON property_listings
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY properties_insert ON property_listings
    FOR INSERT WITH CHECK (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY properties_update ON property_listings
    FOR UPDATE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY properties_delete ON property_listings
    FOR DELETE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY properties_service_all ON property_listings
    FOR ALL USING (auth.role() = 'service_role');

-- Projects
CREATE POLICY projects_select ON projects
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY projects_insert ON projects
    FOR INSERT WITH CHECK (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY projects_update ON projects
    FOR UPDATE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY projects_delete ON projects
    FOR DELETE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY projects_service_all ON projects
    FOR ALL USING (auth.role() = 'service_role');

-- Media Assets
CREATE POLICY media_select ON media_assets
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY media_insert ON media_assets
    FOR INSERT WITH CHECK (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY media_update ON media_assets
    FOR UPDATE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY media_delete ON media_assets
    FOR DELETE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY media_service_all ON media_assets
    FOR ALL USING (auth.role() = 'service_role');

-- Scenes (via project)
CREATE POLICY scenes_select ON scenes
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY scenes_insert ON scenes
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY scenes_update ON scenes
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY scenes_delete ON scenes
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY scenes_service_all ON scenes
    FOR ALL USING (auth.role() = 'service_role');

-- Render Jobs (via project)
CREATE POLICY renders_select ON render_jobs
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY renders_insert ON render_jobs
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY renders_service_all ON render_jobs
    FOR ALL USING (auth.role() = 'service_role');

-- Subscriptions
CREATE POLICY subscriptions_select ON subscriptions
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY subscriptions_service_all ON subscriptions
    FOR ALL USING (auth.role() = 'service_role');

-- Usage Records
CREATE POLICY usage_select ON usage_records
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY usage_service_all ON usage_records
    FOR ALL USING (auth.role() = 'service_role');

-- Social Accounts
CREATE POLICY social_select ON social_accounts
    FOR SELECT USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid()));

CREATE POLICY social_insert ON social_accounts
    FOR INSERT WITH CHECK (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY social_update ON social_accounts
    FOR UPDATE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY social_delete ON social_accounts
    FOR DELETE USING (organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin')));

CREATE POLICY social_service_all ON social_accounts
    FOR ALL USING (auth.role() = 'service_role');

-- Published Content
CREATE POLICY published_select ON published_content
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY published_service_all ON published_content
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- STEP 7: Create Storage Buckets (run in Supabase Dashboard > Storage)
-- ============================================================================

-- Note: Storage bucket creation must be done via Supabase Dashboard or API
-- The following is for reference:
--
-- Bucket: media-assets
--   - Public: false
--   - File size limit: 100MB
--   - Allowed MIME types: image/*, video/*, audio/*
--
-- Bucket: brand-assets  
--   - Public: true (logos, headshots can be public)
--   - File size limit: 10MB
--   - Allowed MIME types: image/*
--
-- Bucket: rendered-videos
--   - Public: false
--   - File size limit: 500MB
--   - Allowed MIME types: video/*

-- ============================================================================
-- STEP 8: Create Useful Views
-- ============================================================================

-- View: Project with related counts
CREATE OR REPLACE VIEW project_summary AS
SELECT 
    p.id,
    p.organization_id,
    p.title,
    p.type,
    p.status,
    p.created_at,
    p.updated_at,
    COUNT(DISTINCT s.id) as scene_count,
    COUNT(DISTINCT m.id) as media_count,
    COUNT(DISTINCT r.id) as render_count,
    MAX(r.completed_at) as last_render_at
FROM projects p
LEFT JOIN scenes s ON s.project_id = p.id
LEFT JOIN media_assets m ON m.project_id = p.id
LEFT JOIN render_jobs r ON r.project_id = p.id AND r.status = 'completed'
GROUP BY p.id;

-- View: Organization usage summary
CREATE OR REPLACE VIEW organization_usage_summary AS
SELECT 
    o.id as organization_id,
    o.name as organization_name,
    s.plan_name,
    s.video_renders_limit,
    s.video_renders_used,
    s.storage_limit_gb,
    s.storage_used_bytes,
    s.current_period_end,
    COUNT(DISTINCT p.id) as total_projects,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'completed') as completed_renders
FROM organizations o
LEFT JOIN subscriptions s ON s.organization_id = o.id
LEFT JOIN projects p ON p.organization_id = o.id
LEFT JOIN render_jobs r ON r.project_id = p.id
GROUP BY o.id, o.name, s.plan_name, s.video_renders_limit, s.video_renders_used, 
         s.storage_limit_gb, s.storage_used_bytes, s.current_period_end;

-- ============================================================================
-- STEP 9: Create Useful Functions
-- ============================================================================

-- Function: Get user's primary organization
CREATE OR REPLACE FUNCTION get_user_primary_organization(user_uuid UUID)
RETURNS UUID AS $$
    SELECT organization_id 
    FROM organization_members 
    WHERE user_id = user_uuid 
    ORDER BY joined_at ASC 
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function: Check if user has access to organization
CREATE OR REPLACE FUNCTION user_has_org_access(user_uuid UUID, org_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM organization_members 
        WHERE user_id = user_uuid AND organization_id = org_uuid
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function: Check if user has admin access to organization
CREATE OR REPLACE FUNCTION user_has_org_admin_access(user_uuid UUID, org_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM organization_members 
        WHERE user_id = user_uuid 
        AND organization_id = org_uuid
        AND role IN ('owner', 'admin')
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function: Increment usage counter
CREATE OR REPLACE FUNCTION increment_usage(
    org_uuid UUID,
    usage_type_param VARCHAR(50),
    amount INTEGER DEFAULT 1
)
RETURNS void AS $$
BEGIN
    -- Record the usage
    INSERT INTO usage_records (organization_id, usage_type, quantity, billing_period)
    VALUES (org_uuid, usage_type_param, amount, TO_CHAR(NOW(), 'YYYY-MM'));
    
    -- Update subscription counters
    IF usage_type_param = 'video_render' THEN
        UPDATE subscriptions 
        SET video_renders_used = video_renders_used + amount
        WHERE organization_id = org_uuid;
    ELSIF usage_type_param = 'ai_script' OR usage_type_param = 'ai_caption' THEN
        UPDATE subscriptions 
        SET ai_generations_used = ai_generations_used + amount
        WHERE organization_id = org_uuid;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Reset monthly usage (call via cron job)
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
    UPDATE subscriptions 
    SET 
        video_renders_used = 0,
        ai_generations_used = 0,
        current_period_start = NOW(),
        current_period_end = NOW() + INTERVAL '1 month'
    WHERE current_period_end < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 10: Create Default Data (Optional)
-- ============================================================================

-- Insert default subscription plans (for reference)
-- This would typically be managed via Stripe

-- DONE!
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts - linked to Supabase Auth';
COMMENT ON TABLE organizations IS 'Multi-tenant organizations/teams';
COMMENT ON TABLE organization_members IS 'Organization membership and roles';
COMMENT ON TABLE brand_kits IS 'Agent branding configurations';
COMMENT ON TABLE property_listings IS 'Real estate property information';
COMMENT ON TABLE projects IS 'Video/infographic projects';
COMMENT ON TABLE media_assets IS 'Uploaded images, videos, audio files';
COMMENT ON TABLE scenes IS 'Video timeline scenes';
COMMENT ON TABLE render_jobs IS 'Video rendering job queue';
COMMENT ON TABLE subscriptions IS 'Billing subscriptions';
COMMENT ON TABLE usage_records IS 'Usage tracking for billing';
COMMENT ON TABLE social_accounts IS 'Connected social media accounts';
COMMENT ON TABLE published_content IS 'Content published to social platforms';

