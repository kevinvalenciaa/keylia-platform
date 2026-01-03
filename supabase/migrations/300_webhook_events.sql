-- This table tracks processed webhook events to prevent duplicate processing
-- when payment providers (Stripe) retry webhook delivery.

CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups by Stripe event ID (used in idempotency check)
CREATE INDEX IF NOT EXISTS idx_webhook_events_stripe_event_id
    ON webhook_events(stripe_event_id);

-- Index for cleanup of old events (events older than 7 days can be purged)
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at
    ON webhook_events(created_at);

-- Comment for documentation
COMMENT ON TABLE webhook_events IS 'Tracks processed webhook events for idempotency. Prevents duplicate processing of Stripe webhooks on retry.';
COMMENT ON COLUMN webhook_events.stripe_event_id IS 'The unique event ID from Stripe (e.g., evt_xxx)';
COMMENT ON COLUMN webhook_events.event_type IS 'The Stripe event type (e.g., checkout.session.completed)';
COMMENT ON COLUMN webhook_events.processed_at IS 'When this event was successfully processed';

-- RLS Policy: Only service role can access this table (webhooks use service role)
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

-- No public access - only service role key can read/write
CREATE POLICY "Service role only" ON webhook_events
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
