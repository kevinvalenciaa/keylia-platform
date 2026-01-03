import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import Stripe from "stripe";
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Billing Router
 *
 * Handles subscription management, checkout sessions, and usage tracking.
 * Works in conjunction with the Stripe webhook handler.
 */

// Stripe client - only initialize if key is provided
const stripe = process.env.STRIPE_SECRET_KEY
  ? new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2025-02-24.acacia",
    })
  : null;

// Plan configuration
const PLANS = {
  starter: {
    name: "Starter",
    priceId: process.env.STRIPE_PRICE_STARTER,
    videoRendersLimit: 20,
    aiGenerationsLimit: 100,
    storageLimitGb: 10,
    teamMembersLimit: 3,
    price: 49,
  },
  professional: {
    name: "Professional",
    priceId: process.env.STRIPE_PRICE_PRO,
    videoRendersLimit: 100,
    aiGenerationsLimit: 500,
    storageLimitGb: 50,
    teamMembersLimit: 10,
    price: 99,
  },
  team: {
    name: "Team",
    priceId: process.env.STRIPE_PRICE_TEAM,
    videoRendersLimit: null, // Unlimited
    aiGenerationsLimit: null,
    storageLimitGb: 200,
    teamMembersLimit: null,
    price: 299,
  },
} as const;

type PlanId = keyof typeof PLANS;

interface OrganizationContext {
  dbUserId: string;
  organizationId: string;
  organizationName: string;
  stripeCustomerId: string | null;
  role: string;
  isOwner: boolean;
}

// Helper to get user's organization context
async function getOrganizationContext(
  supabase: SupabaseClient,
  userId: string
): Promise<OrganizationContext | null> {
  // First get the internal user ID from supabase_id
  const { data: user, error: userError } = await supabase
    .from("users")
    .select("id")
    .eq("supabase_id", userId)
    .single();

  if (userError || !user) {
    return null;
  }

  // Get user's organization membership
  const { data: membership, error: memberError } = await supabase
    .from("organization_members")
    .select("organization_id, role")
    .eq("user_id", user.id)
    .order("joined_at", { ascending: true })
    .limit(1)
    .single();

  if (memberError || !membership) {
    return null;
  }

  // Get organization details
  const { data: organization, error: orgError } = await supabase
    .from("organizations")
    .select("id, name, stripe_customer_id")
    .eq("id", membership.organization_id)
    .single();

  if (orgError || !organization) {
    return null;
  }

  return {
    dbUserId: user.id,
    organizationId: organization.id,
    organizationName: organization.name,
    stripeCustomerId: organization.stripe_customer_id,
    role: membership.role,
    isOwner: membership.role === "owner",
  };
}

export const billingRouter = createTRPCRouter({
  /**
   * Get available subscription plans
   */
  getPlans: protectedProcedure.query(() => {
    return Object.entries(PLANS).map(([id, plan]) => ({
      id,
      name: plan.name,
      videoRendersLimit: plan.videoRendersLimit,
      aiGenerationsLimit: plan.aiGenerationsLimit,
      storageLimitGb: plan.storageLimitGb,
      teamMembersLimit: plan.teamMembersLimit,
      price: plan.price,
    }));
  }),

  /**
   * Create a Stripe Checkout session for subscription
   */
  createCheckoutSession: protectedProcedure
    .input(
      z.object({
        planId: z.enum(["starter", "professional", "team"]),
        trialDays: z.number().min(0).max(30).optional().default(7),
      })
    )
    .mutation(async ({ ctx, input }) => {
      if (!stripe) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message: "Billing is not configured. Contact support.",
        });
      }

      const plan = PLANS[input.planId as PlanId];
      if (!plan.priceId) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: `Plan ${input.planId} is not available.`,
        });
      }

      const org = await getOrganizationContext(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "No organization found. Please complete onboarding.",
        });
      }

      if (!org.isOwner) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Only organization owners can manage billing.",
        });
      }

      // Get or create Stripe customer
      let customerId = org.stripeCustomerId;

      if (!customerId) {
        const customer = await stripe.customers.create({
          email: ctx.user.email,
          name: org.organizationName,
          metadata: {
            supabase_user_id: ctx.user.id,
            organization_id: org.organizationId,
          },
        });
        customerId = customer.id;

        // Save customer ID to organization
        await ctx.supabase
          .from("organizations")
          .update({ stripe_customer_id: customerId })
          .eq("id", org.organizationId);
      }

      // Create checkout session
      const session = await stripe.checkout.sessions.create({
        customer: customerId,
        mode: "subscription",
        payment_method_types: ["card"],
        line_items: [
          {
            price: plan.priceId,
            quantity: 1,
          },
        ],
        success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?checkout=success`,
        cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing?checkout=cancelled`,
        subscription_data: {
          trial_period_days: input.trialDays > 0 ? input.trialDays : undefined,
          metadata: {
            supabase_user_id: ctx.user.id,
            organization_id: org.organizationId,
            plan_id: input.planId,
          },
        },
        allow_promotion_codes: true,
      });

      return { url: session.url };
    }),

  /**
   * Create a Stripe Customer Portal session
   */
  createPortalSession: protectedProcedure.mutation(async ({ ctx }) => {
    if (!stripe) {
      throw new TRPCError({
        code: "PRECONDITION_FAILED",
        message: "Billing is not configured. Contact support.",
      });
    }

    const org = await getOrganizationContext(ctx.supabase, ctx.user.id);
    if (!org) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "No organization found.",
      });
    }

    if (!org.isOwner) {
      throw new TRPCError({
        code: "FORBIDDEN",
        message: "Only organization owners can manage billing.",
      });
    }

    if (!org.stripeCustomerId) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "No active subscription. Please subscribe first.",
      });
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: org.stripeCustomerId,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/settings`,
    });

    return { url: session.url };
  }),

  /**
   * Get current subscription and usage
   */
  getSubscription: protectedProcedure.query(async ({ ctx }) => {
    const org = await getOrganizationContext(ctx.supabase, ctx.user.id);
    if (!org) {
      // Return free tier defaults for users without organization
      return {
        planName: "free",
        status: "active",
        videoRendersUsed: 0,
        videoRendersLimit: 3,
        storageUsedBytes: 0,
        storageLimitGb: 1,
        canGenerate: true,
        isTrial: false,
        trialEndsAt: null,
        currentPeriodEnd: null,
      };
    }

    // Get subscription from database
    const { data: subscription } = await ctx.supabase
      .from("subscriptions")
      .select("*")
      .eq("organization_id", org.organizationId)
      .single();

    if (!subscription) {
      return {
        planName: "free",
        status: "active",
        videoRendersUsed: 0,
        videoRendersLimit: 3,
        storageUsedBytes: 0,
        storageLimitGb: 1,
        canGenerate: true,
        isTrial: false,
        trialEndsAt: null,
        currentPeriodEnd: null,
      };
    }

    const canGenerate =
      subscription.status === "active" || subscription.status === "trialing"
        ? subscription.video_renders_limit === null ||
          subscription.video_renders_used < subscription.video_renders_limit
        : false;

    return {
      planName: subscription.plan_name,
      status: subscription.status,
      videoRendersUsed: subscription.video_renders_used || 0,
      videoRendersLimit: subscription.video_renders_limit,
      storageUsedBytes: subscription.storage_used_bytes || 0,
      storageLimitGb: subscription.storage_limit_gb,
      canGenerate,
      isTrial: subscription.status === "trialing",
      trialEndsAt: subscription.trial_end,
      currentPeriodEnd: subscription.current_period_end,
    };
  }),

  /**
   * Get usage statistics
   */
  getUsage: protectedProcedure.query(async ({ ctx }) => {
    const org = await getOrganizationContext(ctx.supabase, ctx.user.id);
    if (!org) {
      return {
        used: 0,
        limit: 3,
        isTrial: false,
        trialEndsAt: null,
        canGenerate: true,
      };
    }

    const { data: subscription } = await ctx.supabase
      .from("subscriptions")
      .select("status, trial_end, video_renders_used, video_renders_limit")
      .eq("organization_id", org.organizationId)
      .single();

    if (!subscription) {
      return {
        used: 0,
        limit: 3,
        isTrial: false,
        trialEndsAt: null,
        canGenerate: true,
      };
    }

    const isTrial = subscription.status === "trialing";
    const used = subscription.video_renders_used || 0;
    const limit = subscription.video_renders_limit;

    // If Stripe not configured, give unlimited access for testing
    const effectiveLimit = !stripe ? -1 : limit;

    return {
      used,
      limit: effectiveLimit,
      isTrial: stripe ? isTrial : false,
      trialEndsAt: subscription.trial_end,
      canGenerate: effectiveLimit === null || effectiveLimit === -1 || used < effectiveLimit,
    };
  }),

  /**
   * Check if user can generate content
   */
  checkCanGenerate: protectedProcedure.query(async ({ ctx }) => {
    // If Stripe isn't configured, always allow (development mode)
    if (!stripe) {
      return { canGenerate: true, reason: null, remaining: null };
    }

    const org = await getOrganizationContext(ctx.supabase, ctx.user.id);
    if (!org) {
      // Users without organization can generate (during onboarding)
      return { canGenerate: true, reason: null, remaining: null };
    }

    const { data: subscription } = await ctx.supabase
      .from("subscriptions")
      .select("status, trial_end, video_renders_used, video_renders_limit")
      .eq("organization_id", org.organizationId)
      .single();

    if (!subscription) {
      // No subscription = free tier with limited renders
      return { canGenerate: true, reason: null, remaining: 3 };
    }

    // Active subscribers can always generate (up to limit)
    if (subscription.status === "active") {
      const remaining =
        subscription.video_renders_limit === null
          ? null
          : Math.max(
              0,
              subscription.video_renders_limit - (subscription.video_renders_used || 0)
            );

      if (remaining !== null && remaining <= 0) {
        return { canGenerate: false, reason: "limit_reached", remaining: 0 };
      }

      return { canGenerate: true, reason: null, remaining };
    }

    // Check trial
    if (subscription.status === "trialing") {
      const trialEndsAt = subscription.trial_end
        ? new Date(subscription.trial_end)
        : null;

      if (trialEndsAt && trialEndsAt < new Date()) {
        return { canGenerate: false, reason: "trial_expired", remaining: null };
      }

      const limit = subscription.video_renders_limit || 10;
      const used = subscription.video_renders_used || 0;
      const remaining = Math.max(0, limit - used);

      if (remaining <= 0) {
        return { canGenerate: false, reason: "trial_limit_reached", remaining: 0 };
      }

      return { canGenerate: true, reason: null, remaining };
    }

    return { canGenerate: false, reason: "subscription_required", remaining: null };
  }),

  /**
   * Atomically increment video render usage with limit checking.
   * This prevents race conditions where concurrent requests could exceed limits.
   *
   * IMPORTANT: This should be called BEFORE starting a render, not after.
   * The atomic check-and-increment ensures limits are enforced correctly.
   *
   * @returns Object with success status and remaining count
   */
  incrementUsage: protectedProcedure
    .input(
      z.object({
        incrementBy: z.number().int().min(1).max(10).default(1),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getOrganizationContext(ctx.supabase, ctx.user.id);

      if (!org) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "No organization found. Please complete onboarding.",
        });
      }

      // Call the atomic increment function
      // This uses SELECT FOR UPDATE internally to prevent race conditions
      const { data, error } = await ctx.supabase.rpc(
        "increment_video_renders_usage",
        {
          p_organization_id: org.organizationId,
          p_increment_by: input.incrementBy,
        }
      );

      if (error) {
        // If the function doesn't exist yet, fall back to non-atomic check
        if (error.code === "42883") {
          console.warn(
            "increment_video_renders_usage function not found - using fallback"
          );
          return await fallbackIncrementUsage(
            ctx.supabase,
            org.organizationId,
            input.incrementBy
          );
        }
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to update usage",
        });
      }

      const result = Array.isArray(data) ? data[0] : data;

      if (!result?.success) {
        return {
          success: false,
          reason: "limit_reached",
          newCount: result?.new_count ?? 0,
          limit: result?.limit_value ?? 0,
          remaining: result?.remaining ?? 0,
        };
      }

      return {
        success: true,
        reason: null,
        newCount: result.new_count,
        limit: result.limit_value,
        remaining: result.remaining,
      };
    }),

  /**
   * Reserve usage atomically before starting a render.
   * Throws if limit would be exceeded - use for critical paths.
   */
  reserveUsage: protectedProcedure.mutation(async ({ ctx }) => {
    const org = await getOrganizationContext(ctx.supabase, ctx.user.id);

    if (!org) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "No organization found. Please complete onboarding.",
      });
    }

    const { data, error } = await ctx.supabase.rpc(
      "increment_video_renders_usage",
      {
        p_organization_id: org.organizationId,
        p_increment_by: 1,
      }
    );

    if (error) {
      if (error.code === "42883") {
        console.warn(
          "increment_video_renders_usage function not found - using fallback"
        );
        const fallbackResult = await fallbackIncrementUsage(
          ctx.supabase,
          org.organizationId,
          1
        );
        if (!fallbackResult.success) {
          throw new TRPCError({
            code: "FORBIDDEN",
            message: "Usage limit reached. Please upgrade your plan.",
          });
        }
        return { reserved: true, remaining: fallbackResult.remaining };
      }
      throw new TRPCError({
        code: "INTERNAL_SERVER_ERROR",
        message: "Failed to reserve usage",
      });
    }

    const result = Array.isArray(data) ? data[0] : data;

    if (!result?.success) {
      throw new TRPCError({
        code: "FORBIDDEN",
        message: "Usage limit reached. Please upgrade your plan.",
      });
    }

    return {
      reserved: true,
      remaining: result.remaining,
    };
  }),
});

/**
 * Fallback for when the atomic function doesn't exist yet.
 * WARNING: This has a race condition but allows the app to work
 * before migrations are run.
 */
async function fallbackIncrementUsage(
  supabase: SupabaseClient,
  organizationId: string,
  incrementBy: number
): Promise<{
  success: boolean;
  reason: string | null;
  newCount: number;
  limit: number | null;
  remaining: number | null;
}> {
  const { data: subscription } = await supabase
    .from("subscriptions")
    .select("video_renders_used, video_renders_limit, status")
    .eq("organization_id", organizationId)
    .single();

  if (!subscription) {
    return {
      success: false,
      reason: "no_subscription",
      newCount: 0,
      limit: 0,
      remaining: 0,
    };
  }

  if (subscription.status !== "active" && subscription.status !== "trialing") {
    return {
      success: false,
      reason: "inactive",
      newCount: 0,
      limit: 0,
      remaining: 0,
    };
  }

  const currentUsed = subscription.video_renders_used || 0;
  const limit = subscription.video_renders_limit;

  if (limit !== null && currentUsed + incrementBy > limit) {
    return {
      success: false,
      reason: "limit_reached",
      newCount: currentUsed,
      limit: limit,
      remaining: Math.max(0, limit - currentUsed),
    };
  }

  const newCount = currentUsed + incrementBy;
  await supabase
    .from("subscriptions")
    .update({ video_renders_used: newCount })
    .eq("organization_id", organizationId);

  return {
    success: true,
    reason: null,
    newCount,
    limit,
    remaining: limit === null ? null : Math.max(0, limit - newCount),
  };
}
