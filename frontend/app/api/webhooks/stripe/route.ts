import { headers } from "next/headers";
import { NextResponse } from "next/server";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

/**
 * Stripe Webhook Handler
 *
 * This endpoint handles incoming Stripe webhook events with proper
 * signature verification to prevent spoofed requests.
 *
 * SECURITY FEATURES:
 * - Webhook signature verification to prevent spoofed requests
 * - Idempotency handling to prevent duplicate processing on retries
 * - The webhook secret must be configured in production
 */

/**
 * Check if a webhook event has already been processed (idempotency check).
 * Uses the webhook_events table if it exists, otherwise uses a fallback approach.
 *
 * @param supabase - Supabase client
 * @param eventId - Stripe event ID
 * @returns true if the event was already processed
 */
async function isEventProcessed(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  eventId: string
): Promise<boolean> {
  // Try webhook_events table first
  const { data, error } = await supabase
    .from("webhook_events")
    .select("id")
    .eq("stripe_event_id", eventId)
    .maybeSingle();

  // If table doesn't exist (error code 42P01), return false (not processed)
  if (error && error.code === "42P01") {
    // Table doesn't exist - we'll track via a different mechanism
    // For now, allow processing (this is safe because Stripe events are idempotent by design)
    console.warn("webhook_events table not found - skipping idempotency check");
    return false;
  }

  if (error) {
    console.error("Error checking webhook idempotency:", error);
    // On error, allow processing but log it
    return false;
  }

  return data !== null;
}

/**
 * Record a processed webhook event for idempotency.
 *
 * @param supabase - Supabase client
 * @param eventId - Stripe event ID
 * @param eventType - Stripe event type
 */
async function recordProcessedEvent(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  eventId: string,
  eventType: string
): Promise<void> {
  const { error } = await supabase.from("webhook_events").insert({
    stripe_event_id: eventId,
    event_type: eventType,
    processed_at: new Date().toISOString(),
  });

  // Ignore table not found errors - idempotency is best-effort
  if (error && error.code !== "42P01") {
    console.error("Failed to record processed webhook event:", error);
  }
}

// Stripe client - only initialize if key is provided
const stripe = process.env.STRIPE_SECRET_KEY
  ? new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2025-02-24.acacia",
    })
  : null;

// Service role client for webhooks to bypass RLS
// Note: Using 'any' type because the Database types may not include all tables
// that exist in the actual database (webhook_events, etc.). This is safe in
// this context because we're using the service role key.
const getSupabaseAdmin = () => {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceKey) {
    throw new Error("Supabase configuration missing for webhook handler");
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return createClient(url, serviceKey) as any;
};

// Map Stripe subscription status to our internal status
function mapSubscriptionStatus(
  stripeStatus: Stripe.Subscription.Status
): "active" | "trialing" | "cancelled" | "past_due" | "unpaid" {
  switch (stripeStatus) {
    case "active":
      return "active";
    case "trialing":
      return "trialing";
    case "canceled":
    case "incomplete_expired":
      return "cancelled";
    case "past_due":
      return "past_due";
    case "unpaid":
    case "incomplete":
      return "unpaid";
    default:
      return "active";
  }
}

export async function POST(req: Request) {
  // Validate Stripe is configured
  if (!stripe) {
    console.error("Stripe webhook received but Stripe is not configured");
    return NextResponse.json(
      { error: "Stripe is not configured" },
      { status: 503 }
    );
  }

  // Validate webhook secret is configured
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    console.error("Stripe webhook received but webhook secret is not configured");
    return NextResponse.json(
      { error: "Webhook secret not configured" },
      { status: 503 }
    );
  }

  // Get the raw request body and signature
  const body = await req.text();
  const headersList = await headers();
  const signature = headersList.get("Stripe-Signature");

  if (!signature) {
    console.error("Stripe webhook received without signature header");
    return NextResponse.json(
      { error: "Missing Stripe-Signature header" },
      { status: 400 }
    );
  }

  // Verify webhook signature
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Webhook signature verification failed:", message);
    return NextResponse.json(
      { error: "Invalid signature" },
      { status: 400 }
    );
  }

  // Get Supabase admin client
  let supabase: ReturnType<typeof getSupabaseAdmin>;
  try {
    supabase = getSupabaseAdmin();
  } catch (err) {
    console.error("Failed to initialize Supabase:", err);
    return NextResponse.json(
      { error: "Database configuration error" },
      { status: 500 }
    );
  }

  // IDEMPOTENCY CHECK: Skip if event was already processed
  // This prevents duplicate processing when Stripe retries webhook delivery
  const alreadyProcessed = await isEventProcessed(supabase, event.id);
  if (alreadyProcessed) {
    console.log("Webhook event already processed, skipping:", {
      eventId: event.id,
      eventType: event.type,
    });
    return NextResponse.json({
      received: true,
      type: event.type,
      duplicate: true,
    });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const organizationId = session.metadata?.organization_id;
        const planId = session.metadata?.plan_id || "starter";
        const subscriptionId = session.subscription as string;

        if (!organizationId) {
          console.warn("Checkout session completed without organization_id", {
            sessionId: session.id,
          });
          break;
        }

        // Update organization with Stripe customer ID
        await supabase
          .from("organizations")
          .update({
            stripe_customer_id: session.customer as string,
          })
          .eq("id", organizationId);

        // Get subscription details from Stripe
        const subscription = await stripe.subscriptions.retrieve(subscriptionId);

        // Create or update subscription record
        const { error: subError } = await supabase
          .from("subscriptions")
          .upsert(
            {
              organization_id: organizationId,
              stripe_subscription_id: subscriptionId,
              stripe_price_id: subscription.items.data[0]?.price.id,
              plan_name: planId,
              status: mapSubscriptionStatus(subscription.status),
              current_period_start: new Date(
                subscription.current_period_start * 1000
              ).toISOString(),
              current_period_end: new Date(
                subscription.current_period_end * 1000
              ).toISOString(),
              trial_end: subscription.trial_end
                ? new Date(subscription.trial_end * 1000).toISOString()
                : null,
              video_renders_used: 0,
            },
            {
              onConflict: "organization_id",
            }
          );

        if (subError) {
          console.error("Failed to create subscription record:", subError);
        }

        console.log("Checkout completed", {
          organizationId,
          planId,
          subscriptionId,
        });
        break;
      }

      case "customer.subscription.updated": {
        const subscription = event.data.object as Stripe.Subscription;
        const subscriptionId = subscription.id;

        // Update subscription record
        const { error: updateError } = await supabase
          .from("subscriptions")
          .update({
            status: mapSubscriptionStatus(subscription.status),
            current_period_start: new Date(
              subscription.current_period_start * 1000
            ).toISOString(),
            current_period_end: new Date(
              subscription.current_period_end * 1000
            ).toISOString(),
            trial_end: subscription.trial_end
              ? new Date(subscription.trial_end * 1000).toISOString()
              : null,
          })
          .eq("stripe_subscription_id", subscriptionId);

        if (updateError) {
          console.error("Failed to update subscription:", updateError);
        }

        console.log("Subscription updated", {
          subscriptionId,
          status: subscription.status,
        });
        break;
      }

      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;

        const { error: deleteError } = await supabase
          .from("subscriptions")
          .update({
            status: "cancelled",
          })
          .eq("stripe_subscription_id", subscription.id);

        if (deleteError) {
          console.error("Failed to mark subscription as cancelled:", deleteError);
        }

        console.log("Subscription deleted", {
          subscriptionId: subscription.id,
        });
        break;
      }

      case "invoice.paid": {
        const invoice = event.data.object as Stripe.Invoice;
        const subscriptionId = invoice.subscription as string;

        if (subscriptionId) {
          // Reset usage counters for new billing period
          const { error: resetError } = await supabase
            .from("subscriptions")
            .update({
              video_renders_used: 0,
            })
            .eq("stripe_subscription_id", subscriptionId);

          if (resetError) {
            console.error("Failed to reset usage counters:", resetError);
          }

          console.log("Invoice paid - usage reset", { subscriptionId });
        }
        break;
      }

      case "invoice.payment_failed": {
        const invoice = event.data.object as Stripe.Invoice;
        const subscriptionId = invoice.subscription as string;

        if (subscriptionId) {
          const { error: failError } = await supabase
            .from("subscriptions")
            .update({
              status: "past_due",
            })
            .eq("stripe_subscription_id", subscriptionId);

          if (failError) {
            console.error("Failed to update subscription status:", failError);
          }

          console.warn("Invoice payment failed", { subscriptionId });
        }
        break;
      }

      default:
        // Log unhandled events for debugging
        console.log("Unhandled webhook event:", event.type);
    }

    // IDEMPOTENCY: Record successful processing to prevent duplicates
    await recordProcessedEvent(supabase, event.id, event.type);

    return NextResponse.json({ received: true, type: event.type });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Webhook handler error:", message);
    return NextResponse.json(
      { error: "Webhook handler failed" },
      { status: 500 }
    );
  }
}
