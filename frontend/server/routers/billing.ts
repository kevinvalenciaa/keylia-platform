import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import Stripe from "stripe";

// Stripe is optional - only initialize if key is provided
const stripe = process.env.STRIPE_SECRET_KEY
  ? new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2025-02-24.acacia",
    })
  : null;

// Helper to get user's organization
async function getUserOrganization(supabase: any, userId: string) {
  const { data: user, error: userError } = await supabase
    .from("users")
    .select("id")
    .eq("supabase_id", userId)
    .single();

  if (userError || !user) {
    return null;
  }

  const { data: membership, error: memberError } = await supabase
    .from("organization_members")
    .select("organization_id")
    .eq("user_id", user.id)
    .limit(1)
    .single();

  if (memberError || !membership) {
    return null;
  }

  return {
    dbUserId: user.id,
    organizationId: membership.organization_id
  };
}

const PLANS = {
  starter: {
    name: "Starter",
    priceId: process.env.STRIPE_PRICE_STARTER || "price_starter",
    contentLimit: 20,
    price: 49,
  },
  pro: {
    name: "Pro",
    priceId: process.env.STRIPE_PRICE_PRO || "price_pro",
    contentLimit: -1, // unlimited
    price: 99,
  },
};

export const billingRouter = createTRPCRouter({
  getPlans: protectedProcedure.query(() => {
    return Object.entries(PLANS).map(([key, plan]) => ({
      id: key,
      ...plan,
    }));
  }),

  createCheckoutSession: protectedProcedure
    .input(
      z.object({
        planId: z.enum(["starter", "pro"]),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // If Stripe isn't configured, return a message
      if (!stripe) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Stripe is not configured. Payments are disabled.",
        });
      }

      const plan = PLANS[input.planId];

      // Get user's organization
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "No organization found. Please complete onboarding.",
        });
      }

      // Get or create Stripe customer from organization
      const { data: orgData, error } = await ctx.supabase
        .from("organizations")
        .select("stripe_customer_id")
        .eq("id", org.organizationId)
        .single();

      if (error) throw error;

      let customerId = orgData?.stripe_customer_id;

      if (!customerId) {
        const customer = await stripe.customers.create({
          email: ctx.user.email,
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
          trial_period_days: 7,
          metadata: {
            supabase_user_id: ctx.user.id,
            organization_id: org.organizationId,
            plan_id: input.planId,
          },
        },
      });

      return { url: session.url };
    }),

  createPortalSession: protectedProcedure.mutation(async ({ ctx }) => {
    if (!stripe) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "Stripe is not configured. Payments are disabled.",
      });
    }

    // Get user's organization
    const org = await getUserOrganization(ctx.supabase, ctx.user.id);
    if (!org) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "No organization found.",
      });
    }

    const { data: orgData, error } = await ctx.supabase
      .from("organizations")
      .select("stripe_customer_id")
      .eq("id", org.organizationId)
      .single();

    if (error || !orgData?.stripe_customer_id) {
      throw new TRPCError({
        code: "BAD_REQUEST",
        message: "No active subscription found",
      });
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: orgData.stripe_customer_id,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/settings`,
    });

    return { url: session.url };
  }),

  getUsage: protectedProcedure.query(async ({ ctx }) => {
    // Get user's organization
    const org = await getUserOrganization(ctx.supabase, ctx.user.id);
    if (!org) {
      return {
        used: 0,
        limit: -1,
        isTrial: false,
        trialEndsAt: null,
        canGenerate: true,
      };
    }

    // Get subscription from organization
    const { data: subscription } = await ctx.supabase
      .from("subscriptions")
      .select("status, trial_end, video_renders_used, video_renders_limit")
      .eq("organization_id", org.organizationId)
      .single();

    const isTrial = subscription?.status === "trial";
    const trialLimit = subscription?.video_renders_limit || 10;
    const used = subscription?.video_renders_used || 0;
    // If Stripe not configured, give unlimited access for testing
    const limit = !stripe ? -1 : (isTrial ? trialLimit : -1);

    return {
      used,
      limit,
      isTrial: stripe ? isTrial : false, // Don't show trial banner if Stripe disabled
      trialEndsAt: subscription?.trial_end,
      canGenerate: limit === -1 || used < limit,
    };
  }),

  checkCanGenerate: protectedProcedure.query(async ({ ctx }) => {
    // If Stripe not configured, always allow generation for testing
    if (!stripe) {
      return { canGenerate: true, reason: null };
    }

    // Get user's organization
    const org = await getUserOrganization(ctx.supabase, ctx.user.id);
    if (!org) {
      return { canGenerate: true, reason: null }; // Allow if no org yet
    }

    // Get subscription from organization
    const { data: subscription, error } = await ctx.supabase
      .from("subscriptions")
      .select("status, trial_end, video_renders_used, video_renders_limit")
      .eq("organization_id", org.organizationId)
      .single();

    if (error || !subscription) {
      return { canGenerate: true, reason: null }; // Allow if no subscription yet
    }

    // Active subscribers can always generate
    if (subscription.status === "active") {
      return { canGenerate: true, reason: null };
    }

    // Check trial
    if (subscription.status === "trial") {
      const trialEndsAt = subscription.trial_end
        ? new Date(subscription.trial_end)
        : null;

      if (trialEndsAt && trialEndsAt > new Date()) {
        // Check trial usage limit
        const limit = subscription.video_renders_limit || 10;
        const used = subscription.video_renders_used || 0;

        if (used < limit) {
          return {
            canGenerate: true,
            reason: null,
            remaining: limit - used,
          };
        } else {
          return {
            canGenerate: false,
            reason: "trial_limit_reached",
          };
        }
      } else {
        return {
          canGenerate: false,
          reason: "trial_expired",
        };
      }
    }

    return {
      canGenerate: false,
      reason: "subscription_required",
    };
  }),
});
