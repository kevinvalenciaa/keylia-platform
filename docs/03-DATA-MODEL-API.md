# ReelEstate Studio - Data Model & API Design

## 1. Core Entities (ERD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ENTITY RELATIONSHIP DIAGRAM                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│     User      │───────│  Organization │───────│    Team       │
│               │  1:N  │               │  1:N  │   Member      │
└───────┬───────┘       └───────┬───────┘       └───────────────┘
        │                       │
        │                       │ 1:N
        │               ┌───────┴───────┐
        │               │   BrandKit    │
        │               │               │
        │               └───────────────┘
        │
        │ 1:N           ┌───────────────┐       ┌───────────────┐
        └───────────────│    Project    │───────│PropertyListing│
                        │               │  1:1  │               │
                        └───────┬───────┘       └───────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌───────────────┐┌───────────────┐┌───────────────┐
        │    Scene      ││  MediaAsset   ││  RenderJob    │
        │               ││               ││               │
        └───────────────┘└───────────────┘└───────────────┘

┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Subscription  │───────│    Invoice    │       │ SocialAccount │
│               │  1:N  │               │       │               │
└───────────────┘       └───────────────┘       └───────────────┘
```

---

## 2. Detailed Entity Definitions

### 2.1 User
```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255),  -- NULL if OAuth only
    full_name           VARCHAR(255) NOT NULL,
    avatar_url          TEXT,
    phone               VARCHAR(50),
    
    -- OAuth
    google_id           VARCHAR(255) UNIQUE,
    
    -- Status
    email_verified      BOOLEAN DEFAULT FALSE,
    is_active           BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ
);
```

### 2.2 Organization (Multi-tenant)
```sql
CREATE TABLE organizations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    
    -- Owner
    owner_id            UUID REFERENCES users(id) NOT NULL,
    
    -- Settings
    settings            JSONB DEFAULT '{}',
    
    -- Billing
    stripe_customer_id  VARCHAR(255),
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organization_members (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    user_id             UUID REFERENCES users(id) NOT NULL,
    role                VARCHAR(50) DEFAULT 'member',  -- owner, admin, member
    
    -- Timestamps
    joined_at           TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(organization_id, user_id)
);
```

### 2.3 BrandKit
```sql
CREATE TABLE brand_kits (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    is_default          BOOLEAN DEFAULT FALSE,
    
    -- Agent Info
    agent_name          VARCHAR(255),
    agent_title         VARCHAR(255),
    brokerage_name      VARCHAR(255),
    agent_email         VARCHAR(255),
    agent_phone         VARCHAR(50),
    
    -- Visual Identity
    logo_url            TEXT,
    logo_light_url      TEXT,  -- For dark backgrounds
    primary_color       VARCHAR(7),   -- #RRGGBB
    secondary_color     VARCHAR(7),
    accent_color        VARCHAR(7),
    
    -- Typography
    heading_font        VARCHAR(100) DEFAULT 'Inter',
    body_font           VARCHAR(100) DEFAULT 'Inter',
    
    -- Headshot for videos
    headshot_url        TEXT,
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 PropertyListing
```sql
CREATE TABLE property_listings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    
    -- Address
    address_line1       VARCHAR(255) NOT NULL,
    address_line2       VARCHAR(255),
    city                VARCHAR(100) NOT NULL,
    state               VARCHAR(50) NOT NULL,
    zip_code            VARCHAR(20),
    neighborhood        VARCHAR(100),
    
    -- Details
    listing_price       DECIMAL(12, 2),
    bedrooms            SMALLINT,
    bathrooms           DECIMAL(3, 1),
    square_feet         INTEGER,
    lot_size            VARCHAR(50),
    year_built          SMALLINT,
    property_type       VARCHAR(50),  -- single_family, condo, townhouse, etc.
    
    -- Status
    listing_status      VARCHAR(50) DEFAULT 'for_sale',
    -- for_sale, coming_soon, just_listed, open_house, pending, just_sold
    
    -- Features (array)
    features            TEXT[],  -- ['pool', 'renovated_kitchen', 'smart_home']
    
    -- Open House
    open_house_date     DATE,
    open_house_start    TIME,
    open_house_end      TIME,
    
    -- MLS
    mls_number          VARCHAR(50),
    
    -- Positioning
    target_audience     VARCHAR(100),  -- first_time_buyers, luxury, investors
    positioning_notes   TEXT,
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.5 Project
```sql
CREATE TYPE project_type AS ENUM (
    'listing_tour',      -- Type 1: House Listing Tour Video
    'promo_video',       -- Type 2: Realtor On-Camera Promo
    'infographic'        -- Type 3: Static/Animated Graphic
);

CREATE TYPE project_status AS ENUM (
    'draft',
    'script_pending',
    'script_ready',
    'rendering',
    'completed',
    'failed'
);

CREATE TABLE projects (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    created_by_id       UUID REFERENCES users(id) NOT NULL,
    
    -- References
    property_id         UUID REFERENCES property_listings(id),
    brand_kit_id        UUID REFERENCES brand_kits(id),
    
    -- Basic Info
    title               VARCHAR(255) NOT NULL,
    type                project_type NOT NULL,
    status              project_status DEFAULT 'draft',
    
    -- Style Settings
    style_settings      JSONB DEFAULT '{}',
    /*
    {
        "tone": "luxury",           -- luxury, cozy, modern, minimal, bold
        "pace": "moderate",         -- calm, moderate, fast
        "music_vibe": "cinematic",  -- chill, upbeat, cinematic, piano, electronic
        "duration_seconds": 30,     -- 15, 30, 45, 60
        "platform": "instagram_reels",
        "aspect_ratio": "9:16"
    }
    */
    
    -- Voiceover Settings
    voice_settings      JSONB DEFAULT '{}',
    /*
    {
        "enabled": true,
        "language": "en-US",
        "gender": "female",
        "style": "friendly",        -- energetic, calm, authoritative, friendly
        "voice_id": "eleven_labs_voice_id"
    }
    */
    
    -- Infographic Settings (type 3 only)
    infographic_settings JSONB DEFAULT '{}',
    /*
    {
        "layout": "single_card",    -- single_card, carousel_3, carousel_5
        "emphasis": "feature_driven", -- feature_driven, urgency, social_proof
        "animation": "light_motion"  -- static, light_motion
    }
    */
    
    -- Generated Content
    generated_script    JSONB,       -- Full script object
    generated_caption   TEXT,        -- Social media caption
    generated_hashtags  TEXT[],      -- Hashtag recommendations
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.6 Scene (for video projects)
```sql
CREATE TABLE scenes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    
    -- Order
    sequence_order      SMALLINT NOT NULL,
    
    -- Timing
    start_time_ms       INTEGER NOT NULL,
    duration_ms         INTEGER NOT NULL,
    
    -- Content
    narration_text      TEXT,
    on_screen_text      VARCHAR(100),  -- Short, readable on mobile
    
    -- Visual
    media_asset_id      UUID REFERENCES media_assets(id),
    
    -- Camera Movement (shot plan)
    camera_movement     JSONB DEFAULT '{}',
    /*
    {
        "start_position": {"x": 0, "y": 0, "zoom": 1.0},
        "end_position": {"x": 0.1, "y": 0.05, "zoom": 1.2},
        "easing": "ease-in-out",
        "movement_type": "zoom_in"  -- pan_left, pan_right, zoom_in, zoom_out, static
    }
    */
    
    -- Transition
    transition_type     VARCHAR(50) DEFAULT 'crossfade',
    -- crossfade, whip_pan, slide_left, slide_right, zoom_through, cut
    transition_duration_ms INTEGER DEFAULT 500,
    
    -- Overlay Settings
    overlay_settings    JSONB DEFAULT '{}',
    /*
    {
        "show_price": true,
        "show_address": false,
        "show_logo": true,
        "logo_position": "bottom_right",
        "text_position": "bottom_center"
    }
    */
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.7 MediaAsset
```sql
CREATE TYPE media_type AS ENUM (
    'image',
    'video',
    'audio',
    'voiceover',
    'music',
    'logo',
    'headshot'
);

CREATE TYPE media_category AS ENUM (
    'exterior',
    'interior',
    'kitchen',
    'bathroom',
    'bedroom',
    'living_room',
    'backyard',
    'neighborhood',
    'floorplan',
    'agent_selfie',
    'other'
);

CREATE TABLE media_assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    project_id          UUID REFERENCES projects(id),  -- NULL if org-level asset
    
    -- File Info
    filename            VARCHAR(255) NOT NULL,
    file_type           media_type NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    file_size_bytes     BIGINT NOT NULL,
    
    -- Storage
    storage_key         VARCHAR(500) NOT NULL,  -- S3 key
    storage_url         TEXT NOT NULL,          -- CDN URL
    thumbnail_url       TEXT,
    
    -- Metadata
    category            media_category,
    width               INTEGER,
    height              INTEGER,
    duration_seconds    DECIMAL(10, 2),  -- For video/audio
    
    -- AI Analysis
    ai_description      TEXT,            -- Generated description
    ai_tags             TEXT[],          -- Auto-detected tags
    ai_quality_score    DECIMAL(3, 2),   -- 0.00 to 1.00
    
    -- Status
    processing_status   VARCHAR(50) DEFAULT 'pending',
    -- pending, processing, ready, failed
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.8 RenderJob
```sql
CREATE TYPE render_status AS ENUM (
    'queued',
    'processing',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE render_type AS ENUM (
    'preview',          -- Low-res quick preview
    'final',            -- Full-res final render
    'export_variant'    -- Different aspect ratio export
);

CREATE TABLE render_jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id) NOT NULL,
    
    -- Type
    render_type         render_type DEFAULT 'final',
    
    -- Status
    status              render_status DEFAULT 'queued',
    progress_percent    SMALLINT DEFAULT 0,
    
    -- Render Settings
    settings            JSONB DEFAULT '{}',
    /*
    {
        "resolution": "1080x1920",
        "frame_rate": 30,
        "quality": "high",      -- low, medium, high
        "include_captions": true,
        "include_subtitles": true
    }
    */
    
    -- Output
    output_url          TEXT,
    output_file_size    BIGINT,
    subtitle_url        TEXT,           -- SRT/VTT file
    
    -- Error Tracking
    error_message       TEXT,
    error_details       JSONB,
    
    -- Timing
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    
    -- Worker Info
    worker_id           VARCHAR(100),
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.9 Subscription & Billing
```sql
CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    
    -- Stripe
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id     VARCHAR(255),
    
    -- Plan Details
    plan_name           VARCHAR(50) NOT NULL,  -- starter, professional, team, enterprise
    
    -- Limits
    video_renders_limit INTEGER,
    video_renders_used  INTEGER DEFAULT 0,
    storage_limit_gb    INTEGER,
    storage_used_bytes  BIGINT DEFAULT 0,
    
    -- Status
    status              VARCHAR(50) DEFAULT 'active',
    -- active, past_due, cancelled, trialing
    
    -- Period
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    trial_end           TIMESTAMPTZ,
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE usage_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    
    -- Usage Type
    usage_type          VARCHAR(50) NOT NULL,
    -- video_render, infographic_render, ai_script, ai_voice, storage
    
    -- Amount
    quantity            INTEGER DEFAULT 1,
    
    -- Reference
    project_id          UUID REFERENCES projects(id),
    render_job_id       UUID REFERENCES render_jobs(id),
    
    -- Timestamps
    recorded_at         TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.10 SocialAccount (Meta Integration)
```sql
CREATE TABLE social_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id) NOT NULL,
    user_id             UUID REFERENCES users(id) NOT NULL,
    
    -- Platform
    platform            VARCHAR(50) NOT NULL,  -- instagram, facebook
    
    -- Account Info
    platform_user_id    VARCHAR(255) NOT NULL,
    username            VARCHAR(255),
    profile_picture_url TEXT,
    
    -- OAuth Tokens
    access_token        TEXT NOT NULL,
    refresh_token       TEXT,
    token_expires_at    TIMESTAMPTZ,
    
    -- Permissions
    scopes              TEXT[],
    
    -- Status
    is_active           BOOLEAN DEFAULT TRUE,
    last_sync_at        TIMESTAMPTZ,
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(organization_id, platform, platform_user_id)
);
```

---

## 3. API Endpoint Design

### 3.1 Authentication Endpoints

```yaml
POST /api/v1/auth/register
  Description: Register new user with email/password
  Request:
    email: string
    password: string
    full_name: string
  Response: { user, access_token, refresh_token }

POST /api/v1/auth/login
  Description: Login with email/password
  Request:
    email: string
    password: string
  Response: { user, access_token, refresh_token }

POST /api/v1/auth/google
  Description: OAuth login with Google
  Request:
    id_token: string
  Response: { user, access_token, refresh_token, is_new_user }

POST /api/v1/auth/refresh
  Description: Refresh access token
  Request:
    refresh_token: string
  Response: { access_token, refresh_token }

POST /api/v1/auth/logout
  Description: Invalidate tokens
  Response: { success: true }

POST /api/v1/auth/password/reset-request
  Description: Request password reset email
  Request:
    email: string
  Response: { success: true }

POST /api/v1/auth/password/reset
  Description: Reset password with token
  Request:
    token: string
    new_password: string
  Response: { success: true }
```

### 3.2 User & Organization Endpoints

```yaml
GET /api/v1/users/me
  Description: Get current user profile
  Response: { user }

PATCH /api/v1/users/me
  Description: Update user profile
  Request:
    full_name?: string
    phone?: string
    avatar_url?: string
  Response: { user }

GET /api/v1/organizations/current
  Description: Get current organization
  Response: { organization, members, subscription }

PATCH /api/v1/organizations/current
  Description: Update organization settings
  Request:
    name?: string
    settings?: object
  Response: { organization }

POST /api/v1/organizations/current/members
  Description: Invite team member
  Request:
    email: string
    role: "admin" | "member"
  Response: { invitation }

DELETE /api/v1/organizations/current/members/{user_id}
  Description: Remove team member
  Response: { success: true }
```

### 3.3 Brand Kit Endpoints

```yaml
GET /api/v1/brand-kits
  Description: List all brand kits
  Response: { brand_kits: [] }

POST /api/v1/brand-kits
  Description: Create new brand kit
  Request:
    name: string
    agent_name?: string
    agent_title?: string
    brokerage_name?: string
    primary_color?: string
    secondary_color?: string
    heading_font?: string
    body_font?: string
  Response: { brand_kit }

GET /api/v1/brand-kits/{id}
  Description: Get brand kit details
  Response: { brand_kit }

PATCH /api/v1/brand-kits/{id}
  Description: Update brand kit
  Request: (partial brand kit fields)
  Response: { brand_kit }

DELETE /api/v1/brand-kits/{id}
  Description: Delete brand kit
  Response: { success: true }

POST /api/v1/brand-kits/{id}/logo
  Description: Upload logo
  Request: multipart/form-data (file)
  Response: { logo_url }

POST /api/v1/brand-kits/{id}/headshot
  Description: Upload agent headshot
  Request: multipart/form-data (file)
  Response: { headshot_url }
```

### 3.4 Property Listing Endpoints

```yaml
GET /api/v1/properties
  Description: List all properties
  Query: ?status=for_sale&page=1&limit=20
  Response: { properties: [], pagination }

POST /api/v1/properties
  Description: Create new property listing
  Request:
    address_line1: string
    city: string
    state: string
    listing_price?: number
    bedrooms?: number
    bathrooms?: number
    square_feet?: number
    features?: string[]
    listing_status?: string
    target_audience?: string
  Response: { property }

GET /api/v1/properties/{id}
  Description: Get property details
  Response: { property, projects: [] }

PATCH /api/v1/properties/{id}
  Description: Update property
  Request: (partial property fields)
  Response: { property }

DELETE /api/v1/properties/{id}
  Description: Delete property (soft delete)
  Response: { success: true }
```

### 3.5 Project Endpoints

```yaml
GET /api/v1/projects
  Description: List all projects
  Query: ?type=listing_tour&status=completed&property_id=uuid&page=1&limit=20
  Response: { projects: [], pagination }

POST /api/v1/projects
  Description: Create new project
  Request:
    title: string
    type: "listing_tour" | "promo_video" | "infographic"
    property_id?: uuid
    brand_kit_id?: uuid
    style_settings?: object
    voice_settings?: object
    infographic_settings?: object
  Response: { project }

GET /api/v1/projects/{id}
  Description: Get project with scenes and assets
  Response: { project, scenes: [], media_assets: [], render_jobs: [] }

PATCH /api/v1/projects/{id}
  Description: Update project settings
  Request: (partial project fields)
  Response: { project }

DELETE /api/v1/projects/{id}
  Description: Delete project
  Response: { success: true }

POST /api/v1/projects/{id}/duplicate
  Description: Duplicate project
  Request:
    new_title?: string
  Response: { project }
```

### 3.6 Scene Endpoints (Video Projects)

```yaml
GET /api/v1/projects/{project_id}/scenes
  Description: Get all scenes for a project
  Response: { scenes: [] }

POST /api/v1/projects/{project_id}/scenes
  Description: Add new scene
  Request:
    sequence_order: number
    duration_ms: number
    narration_text?: string
    on_screen_text?: string
    media_asset_id?: uuid
    camera_movement?: object
    transition_type?: string
  Response: { scene }

PATCH /api/v1/projects/{project_id}/scenes/{scene_id}
  Description: Update scene
  Request: (partial scene fields)
  Response: { scene }

DELETE /api/v1/projects/{project_id}/scenes/{scene_id}
  Description: Delete scene
  Response: { success: true }

POST /api/v1/projects/{project_id}/scenes/reorder
  Description: Reorder all scenes
  Request:
    scene_order: [{ scene_id: uuid, sequence_order: number }]
  Response: { scenes: [] }
```

### 3.7 Media Asset Endpoints

```yaml
GET /api/v1/media
  Description: List organization media assets
  Query: ?type=image&category=exterior&project_id=uuid&page=1&limit=50
  Response: { media_assets: [], pagination }

POST /api/v1/media/upload-url
  Description: Get presigned upload URL
  Request:
    filename: string
    mime_type: string
    file_size: number
    project_id?: uuid
    category?: string
  Response: { upload_url, asset_id, storage_key }

POST /api/v1/media/{id}/confirm-upload
  Description: Confirm upload completed
  Response: { media_asset }

DELETE /api/v1/media/{id}
  Description: Delete media asset
  Response: { success: true }

POST /api/v1/media/{id}/analyze
  Description: Trigger AI analysis of media
  Response: { job_id }
```

### 3.8 AI Generation Endpoints

```yaml
POST /api/v1/ai/generate-script
  Description: Generate full script for video project
  Request:
    project_id: uuid
    regenerate?: boolean
  Response: { script, scenes: [] }

POST /api/v1/ai/regenerate-scene-text
  Description: Regenerate text for specific scene
  Request:
    scene_id: uuid
  Response: { scene }

POST /api/v1/ai/generate-caption
  Description: Generate social media caption
  Request:
    project_id: uuid
  Response: { caption, hashtags, first_comment }

POST /api/v1/ai/generate-shot-plan
  Description: Generate camera movements for scenes
  Request:
    project_id: uuid
  Response: { scenes: [] }

POST /api/v1/ai/generate-layouts
  Description: Generate infographic layout options
  Request:
    project_id: uuid
    count?: number (default 3)
  Response: { layouts: [] }

POST /api/v1/ai/analyze-photos
  Description: Analyze uploaded photos
  Request:
    media_asset_ids: uuid[]
  Response: { analyses: [] }
```

### 3.9 Render Job Endpoints

```yaml
GET /api/v1/projects/{project_id}/renders
  Description: List render jobs for project
  Response: { render_jobs: [] }

POST /api/v1/projects/{project_id}/renders
  Description: Start new render job
  Request:
    render_type?: "preview" | "final"
    settings?: {
      resolution?: string
      frame_rate?: number
      include_captions?: boolean
      include_subtitles?: boolean
    }
  Response: { render_job }

GET /api/v1/renders/{id}
  Description: Get render job status
  Response: { render_job }

DELETE /api/v1/renders/{id}
  Description: Cancel render job
  Response: { success: true }

# WebSocket for real-time updates
WS /api/v1/ws/renders/{id}
  Description: Subscribe to render progress
  Messages: { type: "progress", percent: 45 } | { type: "completed", url: "..." }
```

### 3.10 Billing Endpoints

```yaml
GET /api/v1/billing/subscription
  Description: Get current subscription
  Response: { subscription, usage }

POST /api/v1/billing/checkout
  Description: Create Stripe checkout session
  Request:
    plan: "starter" | "professional" | "team"
    billing_cycle: "monthly" | "yearly"
  Response: { checkout_url }

POST /api/v1/billing/portal
  Description: Get Stripe customer portal URL
  Response: { portal_url }

GET /api/v1/billing/usage
  Description: Get usage statistics
  Query: ?period=current | ?start_date=2024-01-01&end_date=2024-01-31
  Response: { usage_records: [], summary }

POST /api/v1/billing/webhooks/stripe
  Description: Handle Stripe webhooks
  Request: Stripe event payload
  Response: { received: true }
```

### 3.11 Social Account Endpoints

```yaml
GET /api/v1/social-accounts
  Description: List connected social accounts
  Response: { accounts: [] }

POST /api/v1/social-accounts/connect/instagram
  Description: Initiate Instagram OAuth
  Response: { auth_url }

POST /api/v1/social-accounts/callback/instagram
  Description: Handle Instagram OAuth callback
  Request:
    code: string
  Response: { account }

DELETE /api/v1/social-accounts/{id}
  Description: Disconnect social account
  Response: { success: true }

POST /api/v1/social-accounts/{id}/publish
  Description: Publish content to social platform
  Request:
    project_id: uuid
    render_job_id: uuid
    caption: string
    scheduled_at?: timestamp
  Response: { post_id, status }
```

---

## 4. Request/Response Schemas (Pydantic)

```python
# Example Pydantic schemas for key endpoints

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    type: Literal["listing_tour", "promo_video", "infographic"]
    property_id: Optional[UUID] = None
    brand_kit_id: Optional[UUID] = None
    style_settings: Optional[StyleSettings] = None
    voice_settings: Optional[VoiceSettings] = None
    infographic_settings: Optional[InfographicSettings] = None

class StyleSettings(BaseModel):
    tone: Literal["luxury", "cozy", "modern", "minimal", "bold"] = "modern"
    pace: Literal["calm", "moderate", "fast"] = "moderate"
    music_vibe: Literal["chill", "upbeat", "cinematic", "piano", "electronic"] = "cinematic"
    duration_seconds: Literal[15, 30, 45, 60] = 30
    platform: Literal["instagram_reels", "facebook_reels", "ig_story", "ig_feed", "fb_feed"] = "instagram_reels"
    aspect_ratio: Literal["9:16", "1:1", "4:5"] = "9:16"

class VoiceSettings(BaseModel):
    enabled: bool = True
    language: str = "en-US"
    gender: Literal["male", "female", "neutral"] = "female"
    style: Literal["energetic", "calm", "authoritative", "friendly"] = "friendly"
    voice_id: Optional[str] = None

class SceneResponse(BaseModel):
    id: UUID
    sequence_order: int
    start_time_ms: int
    duration_ms: int
    narration_text: Optional[str]
    on_screen_text: Optional[str]
    media_asset: Optional[MediaAssetResponse]
    camera_movement: CameraMovement
    transition_type: str
    overlay_settings: OverlaySettings

class RenderJobResponse(BaseModel):
    id: UUID
    project_id: UUID
    render_type: str
    status: str
    progress_percent: int
    output_url: Optional[str]
    subtitle_url: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
```

---

## 5. Database Indexes

```sql
-- Performance indexes
CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_type ON projects(type);
CREATE INDEX idx_projects_created ON projects(created_at DESC);

CREATE INDEX idx_scenes_project ON scenes(project_id);
CREATE INDEX idx_scenes_order ON scenes(project_id, sequence_order);

CREATE INDEX idx_media_org ON media_assets(organization_id);
CREATE INDEX idx_media_project ON media_assets(project_id);
CREATE INDEX idx_media_type ON media_assets(file_type);

CREATE INDEX idx_render_jobs_project ON render_jobs(project_id);
CREATE INDEX idx_render_jobs_status ON render_jobs(status);

CREATE INDEX idx_properties_org ON property_listings(organization_id);
CREATE INDEX idx_properties_status ON property_listings(listing_status);

-- Full-text search
CREATE INDEX idx_properties_search ON property_listings 
  USING GIN(to_tsvector('english', address_line1 || ' ' || city || ' ' || neighborhood));
```

