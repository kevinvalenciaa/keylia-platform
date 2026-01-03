-- =============================================================================
-- Keylia - Storage Buckets & Policies
-- =============================================================================
-- Run this AFTER 001_initial_schema.sql
-- =============================================================================

-- ============================================================================
-- Storage Bucket Policies (RLS for Storage)
-- ============================================================================

-- Note: Buckets must be created via Supabase Dashboard first:
-- 1. Go to Storage > New Bucket
-- 2. Create: "media-assets" (private), "brand-assets" (public), "rendered-videos" (private)

-- -----------------------------------------------------------------------------
-- media-assets bucket policies
-- -----------------------------------------------------------------------------

-- Policy: Users can upload to their organization's folder
CREATE POLICY "Users can upload media to their org"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'media-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Users can view their organization's media
CREATE POLICY "Users can view their org media"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'media-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Users can update their organization's media
CREATE POLICY "Users can update their org media"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'media-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Admins can delete their organization's media
CREATE POLICY "Admins can delete org media"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'media-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
);

-- -----------------------------------------------------------------------------
-- brand-assets bucket policies (public bucket)
-- -----------------------------------------------------------------------------

-- Policy: Users can upload brand assets to their org folder
CREATE POLICY "Users can upload brand assets to their org"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'brand-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Anyone can view brand assets (public logos, etc.)
CREATE POLICY "Public can view brand assets"
ON storage.objects FOR SELECT
USING (bucket_id = 'brand-assets');

-- Policy: Org members can update their brand assets
CREATE POLICY "Users can update their org brand assets"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'brand-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Admins can delete brand assets
CREATE POLICY "Admins can delete brand assets"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'brand-assets' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
);

-- -----------------------------------------------------------------------------
-- rendered-videos bucket policies
-- -----------------------------------------------------------------------------

-- Policy: Service role can upload rendered videos (from backend workers)
CREATE POLICY "Service can upload rendered videos"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'rendered-videos' AND
    auth.role() = 'service_role'
);

-- Policy: Users can view their organization's rendered videos
CREATE POLICY "Users can view their org rendered videos"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'rendered-videos' AND
    (storage.foldername(name))[1] IN (
        SELECT organization_id::text 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Service role can manage all rendered videos
CREATE POLICY "Service can manage rendered videos"
ON storage.objects FOR ALL
USING (
    bucket_id = 'rendered-videos' AND
    auth.role() = 'service_role'
);

-- ============================================================================
-- Additional Indexes for Performance
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_projects_org_status_created 
    ON projects(organization_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_renders_project_status_created 
    ON render_jobs(project_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_org_type_created 
    ON media_assets(organization_id, file_type, created_at DESC);

-- Partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_projects_active 
    ON projects(organization_id, created_at DESC) 
    WHERE status NOT IN ('archived', 'failed');

CREATE INDEX IF NOT EXISTS idx_subscriptions_active 
    ON subscriptions(organization_id) 
    WHERE status = 'active';

-- ============================================================================
-- Database Maintenance Functions
-- ============================================================================

-- Function: Clean up orphaned media assets
CREATE OR REPLACE FUNCTION cleanup_orphaned_media()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM media_assets
        WHERE project_id IS NOT NULL 
        AND project_id NOT IN (SELECT id FROM projects)
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Archive old completed projects
CREATE OR REPLACE FUNCTION archive_old_projects(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    WITH archived AS (
        UPDATE projects
        SET status = 'archived'
        WHERE status = 'completed'
        AND updated_at < NOW() - (days_old || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO archived_count FROM archived;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get storage usage for organization
CREATE OR REPLACE FUNCTION get_org_storage_usage(org_uuid UUID)
RETURNS TABLE (
    total_bytes BIGINT,
    image_bytes BIGINT,
    video_bytes BIGINT,
    audio_bytes BIGINT,
    file_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(file_size_bytes), 0)::BIGINT as total_bytes,
        COALESCE(SUM(CASE WHEN file_type = 'image' THEN file_size_bytes ELSE 0 END), 0)::BIGINT as image_bytes,
        COALESCE(SUM(CASE WHEN file_type = 'video' THEN file_size_bytes ELSE 0 END), 0)::BIGINT as video_bytes,
        COALESCE(SUM(CASE WHEN file_type IN ('audio', 'voiceover', 'music') THEN file_size_bytes ELSE 0 END), 0)::BIGINT as audio_bytes,
        COUNT(*)::BIGINT as file_count
    FROM media_assets
    WHERE organization_id = org_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- Scheduled Jobs Setup (via pg_cron if available, or Supabase Edge Functions)
-- ============================================================================

-- Note: Supabase doesn't have pg_cron by default. 
-- Use Supabase Edge Functions or external cron to run these:
--
-- Daily:
--   SELECT cleanup_orphaned_media();
--   SELECT archive_old_projects(90);
--
-- Monthly (1st of month):
--   SELECT reset_monthly_usage();

-- ============================================================================
-- Audit Logging (Optional but Recommended for Production)
-- ============================================================================

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_logs(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_changed_by ON audit_logs(changed_by) WHERE changed_by IS NOT NULL;

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_data, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', to_jsonb(OLD), auth.uid());
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), auth.uid());
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (table_name, record_id, action, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', to_jsonb(NEW), auth.uid());
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to sensitive tables
CREATE TRIGGER audit_projects
    AFTER INSERT OR UPDATE OR DELETE ON projects
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_subscriptions
    AFTER INSERT OR UPDATE OR DELETE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_organization_members
    AFTER INSERT OR UPDATE OR DELETE ON organization_members
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- RLS for audit_logs (only service role and admins can view)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_logs_service ON audit_logs
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- DONE!
-- ============================================================================

