-- =============================================================================
-- Add DELETE policy for render_jobs table
-- =============================================================================
-- This allows users to delete render jobs for projects in their organizations

CREATE POLICY "Users can delete org render jobs" ON render_jobs
  FOR DELETE USING (
    project_id IN (
      SELECT p.id FROM projects p
      WHERE p.organization_id IN (
        SELECT om.organization_id FROM organization_members om
        JOIN users u ON om.user_id = u.id
        WHERE u.supabase_id = auth.uid()::text
      )
    )
  );
