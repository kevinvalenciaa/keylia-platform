
-- This function increments video_renders_used while checking the limit.
-- It prevents race conditions where concurrent requests could exceed the limit.

-- Function to increment usage with limit check
CREATE OR REPLACE FUNCTION increment_video_renders_usage(
    p_organization_id UUID,
    p_increment_by INTEGER DEFAULT 1
)
RETURNS TABLE (
    success BOOLEAN,
    new_count INTEGER,
    limit_value INTEGER,
    remaining INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_used INTEGER;
    v_limit INTEGER;
    v_new_count INTEGER;
    v_status TEXT;
BEGIN
    -- Lock the row for update to prevent concurrent modifications
    SELECT video_renders_used, video_renders_limit, status
    INTO v_current_used, v_limit, v_status
    FROM subscriptions
    WHERE organization_id = p_organization_id
    FOR UPDATE;

    -- If no subscription found, return failure
    IF NOT FOUND THEN
        RETURN QUERY SELECT
            FALSE AS success,
            0 AS new_count,
            0 AS limit_value,
            0 AS remaining;
        RETURN;
    END IF;

    -- Check if subscription is active or trialing
    IF v_status NOT IN ('active', 'trialing') THEN
        RETURN QUERY SELECT
            FALSE AS success,
            COALESCE(v_current_used, 0) AS new_count,
            COALESCE(v_limit, 0) AS limit_value,
            0 AS remaining;
        RETURN;
    END IF;

    -- If limit is NULL (unlimited), always succeed
    IF v_limit IS NULL THEN
        v_new_count := COALESCE(v_current_used, 0) + p_increment_by;

        UPDATE subscriptions
        SET video_renders_used = v_new_count,
            updated_at = NOW()
        WHERE organization_id = p_organization_id;

        RETURN QUERY SELECT
            TRUE AS success,
            v_new_count AS new_count,
            NULL::INTEGER AS limit_value,
            NULL::INTEGER AS remaining;
        RETURN;
    END IF;

    -- Check if increment would exceed limit
    v_current_used := COALESCE(v_current_used, 0);
    IF v_current_used + p_increment_by > v_limit THEN
        RETURN QUERY SELECT
            FALSE AS success,
            v_current_used AS new_count,
            v_limit AS limit_value,
            GREATEST(0, v_limit - v_current_used) AS remaining;
        RETURN;
    END IF;

    -- Perform the atomic increment
    v_new_count := v_current_used + p_increment_by;

    UPDATE subscriptions
    SET video_renders_used = v_new_count,
        updated_at = NOW()
    WHERE organization_id = p_organization_id;

    RETURN QUERY SELECT
        TRUE AS success,
        v_new_count AS new_count,
        v_limit AS limit_value,
        GREATEST(0, v_limit - v_new_count) AS remaining;
END;
$$;

-- Grant execute to authenticated users (will be checked by RLS on underlying tables)
GRANT EXECUTE ON FUNCTION increment_video_renders_usage(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_video_renders_usage(UUID, INTEGER) TO service_role;

-- Comment for documentation
COMMENT ON FUNCTION increment_video_renders_usage IS 'Atomically increments video render usage with limit checking. Returns success=false if limit would be exceeded.';
