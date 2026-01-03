-- =============================================================================
-- ReelEstate Studio - Seed Data (Optional)
-- =============================================================================
-- Run this AFTER 001 and 002 migrations if you want sample data
-- =============================================================================

-- ============================================================================
-- Default Subscription Plans Reference
-- ============================================================================

-- Note: These are for reference. Actual plans should be managed in Stripe.
-- The plan_name values that should match Stripe:

/*
Plan Tiers:
-----------
1. free
   - video_renders_limit: 3
   - ai_generations_limit: 10
   - storage_limit_gb: 1
   - team_members_limit: 1

2. starter ($29/month)
   - video_renders_limit: 15
   - ai_generations_limit: 50
   - storage_limit_gb: 10
   - team_members_limit: 1

3. professional ($79/month)
   - video_renders_limit: 50
   - ai_generations_limit: 200
   - storage_limit_gb: 50
   - team_members_limit: 3

4. team ($199/month)
   - video_renders_limit: 200
   - ai_generations_limit: unlimited
   - storage_limit_gb: 200
   - team_members_limit: 10

5. enterprise (custom)
   - All unlimited
   - Custom pricing
*/

-- ============================================================================
-- Create Demo/Test Data (Only for Development)
-- ============================================================================

-- Only run this in development environments!
-- Comment out or skip for production.

DO $$
DECLARE
    demo_user_id UUID;
    demo_org_id UUID;
    demo_brand_kit_id UUID;
    demo_property_id UUID;
    demo_project_id UUID;
BEGIN
    -- Check if we're in a dev environment (you might want to add a check here)
    -- IF current_database() != 'reelestate_dev' THEN
    --     RAISE NOTICE 'Skipping seed data - not in dev environment';
    --     RETURN;
    -- END IF;

    -- Skip if data already exists
    IF EXISTS (SELECT 1 FROM users WHERE email = 'demo@reelestate.studio') THEN
        RAISE NOTICE 'Demo data already exists, skipping...';
        RETURN;
    END IF;

    -- Create demo user
    INSERT INTO users (id, email, password_hash, full_name, email_verified, is_active)
    VALUES (
        uuid_generate_v4(),
        'demo@reelestate.studio',
        -- Password: "demo123" (bcrypt hash)
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.AqR5E5wC5R5wC5',
        'Demo Agent',
        TRUE,
        TRUE
    )
    RETURNING id INTO demo_user_id;

    RAISE NOTICE 'Created demo user: %', demo_user_id;

    -- Create demo organization
    INSERT INTO organizations (id, name, slug, owner_id)
    VALUES (
        uuid_generate_v4(),
        'Demo Real Estate',
        'demo-real-estate',
        demo_user_id
    )
    RETURNING id INTO demo_org_id;

    RAISE NOTICE 'Created demo organization: %', demo_org_id;

    -- Add user as organization owner
    INSERT INTO organization_members (organization_id, user_id, role)
    VALUES (demo_org_id, demo_user_id, 'owner');

    -- Create demo subscription (free tier)
    INSERT INTO subscriptions (
        organization_id,
        plan_name,
        video_renders_limit,
        ai_generations_limit,
        storage_limit_gb,
        status,
        current_period_start,
        current_period_end
    )
    VALUES (
        demo_org_id,
        'free',
        3,
        10,
        1,
        'active',
        NOW(),
        NOW() + INTERVAL '30 days'
    );

    -- Create demo brand kit
    INSERT INTO brand_kits (
        id,
        organization_id,
        name,
        is_default,
        agent_name,
        agent_title,
        brokerage_name,
        agent_email,
        agent_phone,
        primary_color,
        secondary_color,
        accent_color
    )
    VALUES (
        uuid_generate_v4(),
        demo_org_id,
        'Default Brand Kit',
        TRUE,
        'Demo Agent',
        'Licensed Real Estate Agent',
        'Demo Realty Group',
        'demo@reelestate.studio',
        '(555) 123-4567',
        '#2563eb',
        '#1e40af',
        '#f59e0b'
    )
    RETURNING id INTO demo_brand_kit_id;

    RAISE NOTICE 'Created demo brand kit: %', demo_brand_kit_id;

    -- Create demo property listing
    INSERT INTO property_listings (
        id,
        organization_id,
        address_line1,
        city,
        state,
        zip_code,
        neighborhood,
        listing_price,
        bedrooms,
        bathrooms,
        square_feet,
        year_built,
        property_type,
        listing_status,
        features,
        target_audience
    )
    VALUES (
        uuid_generate_v4(),
        demo_org_id,
        '123 Demo Street',
        'Los Angeles',
        'CA',
        '90210',
        'Beverly Hills',
        1250000.00,
        4,
        3.5,
        3200,
        2018,
        'single_family',
        'for_sale',
        ARRAY['Pool', 'Smart Home', 'Open Floor Plan', 'Gourmet Kitchen', 'Home Office'],
        'Young professionals and growing families'
    )
    RETURNING id INTO demo_property_id;

    RAISE NOTICE 'Created demo property: %', demo_property_id;

    -- Create demo project
    INSERT INTO projects (
        id,
        organization_id,
        created_by_id,
        property_id,
        brand_kit_id,
        title,
        type,
        status,
        style_settings,
        voice_settings
    )
    VALUES (
        uuid_generate_v4(),
        demo_org_id,
        demo_user_id,
        demo_property_id,
        demo_brand_kit_id,
        'Beverly Hills Listing Tour',
        'listing_tour',
        'draft',
        '{
            "tone": "luxury",
            "pace": "moderate",
            "music_vibe": "cinematic",
            "duration_seconds": 30,
            "platform": "instagram_reels",
            "aspect_ratio": "9:16"
        }'::jsonb,
        '{
            "enabled": true,
            "language": "en-US",
            "gender": "female",
            "style": "professional"
        }'::jsonb
    )
    RETURNING id INTO demo_project_id;

    RAISE NOTICE 'Created demo project: %', demo_project_id;

    -- Create demo scenes for the project
    INSERT INTO scenes (project_id, sequence_order, start_time_ms, duration_ms, narration_text, on_screen_text, camera_movement, transition_type)
    VALUES
    (demo_project_id, 1, 0, 5000, 
     'Welcome to this stunning Beverly Hills estate',
     'BEVERLY HILLS',
     '{"type": "zoom_out", "easing": "ease-in-out"}'::jsonb,
     'fade_black'),
    (demo_project_id, 2, 5000, 5000,
     'Featuring 4 bedrooms and 3.5 baths across 3,200 square feet',
     '4 BD | 3.5 BA | 3,200 SF',
     '{"type": "pan_right", "easing": "ease-in-out"}'::jsonb,
     'crossfade'),
    (demo_project_id, 3, 10000, 5000,
     'The gourmet kitchen is perfect for entertaining',
     'GOURMET KITCHEN',
     '{"type": "zoom_in", "easing": "ease-in-out"}'::jsonb,
     'crossfade'),
    (demo_project_id, 4, 15000, 5000,
     'Step outside to your private oasis with sparkling pool',
     'PRIVATE POOL',
     '{"type": "pan_left", "easing": "ease-in-out"}'::jsonb,
     'crossfade'),
    (demo_project_id, 5, 20000, 5000,
     'Smart home features throughout for modern living',
     'SMART HOME',
     '{"type": "zoom_in", "easing": "ease-in-out"}'::jsonb,
     'crossfade'),
    (demo_project_id, 6, 25000, 5000,
     'Schedule your private showing today. Link in bio.',
     'SCHEDULE SHOWING',
     '{"type": "zoom_out", "easing": "ease-out"}'::jsonb,
     'fade_black');

    RAISE NOTICE 'Created 6 demo scenes for project';

    RAISE NOTICE 'Demo data created successfully!';
    RAISE NOTICE 'Demo login: demo@reelestate.studio / demo123';

END $$;

-- ============================================================================
-- Verify Seed Data
-- ============================================================================

-- Run this to verify the seed data was created:
/*
SELECT 
    u.email,
    o.name as org_name,
    s.plan_name,
    COUNT(DISTINCT p.id) as project_count,
    COUNT(DISTINCT bk.id) as brand_kit_count,
    COUNT(DISTINCT pl.id) as property_count
FROM users u
JOIN organization_members om ON om.user_id = u.id
JOIN organizations o ON o.id = om.organization_id
LEFT JOIN subscriptions s ON s.organization_id = o.id
LEFT JOIN projects p ON p.organization_id = o.id
LEFT JOIN brand_kits bk ON bk.organization_id = o.id
LEFT JOIN property_listings pl ON pl.organization_id = o.id
WHERE u.email = 'demo@reelestate.studio'
GROUP BY u.email, o.name, s.plan_name;
*/

