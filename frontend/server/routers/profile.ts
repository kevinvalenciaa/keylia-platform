import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";

export const profileRouter = createTRPCRouter({
  get: protectedProcedure.query(async ({ ctx }) => {
    // Get user from users table by supabase_id
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: userData, error } = await (ctx.supabase as any)
      .from("users")
      .select("*")
      .eq("supabase_id", ctx.user.id)
      .single();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const user = userData as any;

    if (error || !user) {
      // Return default profile structure if user not found
      // User will be created by backend on first API call
      return {
        id: ctx.user.id,
        full_name: ctx.user.email?.split("@")[0] || "",
        brokerage: null,
        phone: null,
        subscription_status: "trial" as const,
        stripe_customer_id: null,
        trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    // Get subscription info from organization
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: membership } = await (ctx.supabase as any)
      .from("organization_members")
      .select("organization_id")
      .eq("user_id", user.id)
      .limit(1)
      .single();

    let subscriptionStatus = "trial";
    let trialEndsAt = null;
    let stripeCustomerId = null;

    if (membership) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: subscription } = await (ctx.supabase as any)
        .from("subscriptions")
        .select("status, trial_end")
        .eq("organization_id", membership.organization_id)
        .single();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: org } = await (ctx.supabase as any)
        .from("organizations")
        .select("stripe_customer_id")
        .eq("id", membership.organization_id)
        .single();

      if (subscription) {
        subscriptionStatus = subscription.status || "trial";
        trialEndsAt = subscription.trial_end;
      }
      if (org) {
        stripeCustomerId = org.stripe_customer_id;
      }
    }

    return {
      id: ctx.user.id,
      full_name: user.full_name || "",
      brokerage: null, // Backend schema doesn't have brokerage on users
      phone: user.phone,
      subscription_status: subscriptionStatus as "trial" | "active" | "cancelled" | "past_due",
      stripe_customer_id: stripeCustomerId,
      trial_ends_at: trialEndsAt,
      created_at: user.created_at,
      updated_at: user.updated_at,
    };
  }),

  update: protectedProcedure
    .input(
      z.object({
        full_name: z.string().min(1).optional(),
        brokerage: z.string().optional(),
        phone: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: userData, error: userError } = await (ctx.supabase as any)
        .from("users")
        .select("id")
        .eq("supabase_id", ctx.user.id)
        .single();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const user = userData as any;

      if (userError || !user) {
        throw new Error("User not found");
      }

      const updates: {
        full_name?: string;
        phone?: string;
        updated_at: string;
      } = {
        updated_at: new Date().toISOString(),
      };
      if (input.full_name !== undefined) updates.full_name = input.full_name;
      if (input.phone !== undefined) updates.phone = input.phone;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("users")
        .update(updates)
        .eq("id", user.id)
        .select()
        .single();

      if (error) throw error;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const updatedUser = data as any;

      return {
        id: ctx.user.id,
        full_name: updatedUser.full_name || "",
        brokerage: null,
        phone: updatedUser.phone,
        subscription_status: "trial" as const,
        stripe_customer_id: null,
        trial_ends_at: null,
        created_at: updatedUser.created_at,
        updated_at: updatedUser.updated_at,
      };
    }),

  getSubscriptionStatus: protectedProcedure.query(async ({ ctx }) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: userData } = await (ctx.supabase as any)
      .from("users")
      .select("id")
      .eq("supabase_id", ctx.user.id)
      .single();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const user = userData as any;

    if (!user) {
      return {
        subscription_status: "trial",
        trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        stripe_customer_id: null,
        isTrialActive: true,
        canGenerate: true,
      };
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: membership } = await (ctx.supabase as any)
      .from("organization_members")
      .select("organization_id")
      .eq("user_id", user.id)
      .limit(1)
      .single();

    if (!membership) {
      return {
        subscription_status: "trial",
        trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        stripe_customer_id: null,
        isTrialActive: true,
        canGenerate: true,
      };
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: subscription } = await (ctx.supabase as any)
      .from("subscriptions")
      .select("status, trial_end")
      .eq("organization_id", membership.organization_id)
      .single();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: org } = await (ctx.supabase as any)
      .from("organizations")
      .select("stripe_customer_id")
      .eq("id", membership.organization_id)
      .single();

    const status = subscription?.status || "trial";
    const trialEnd = subscription?.trial_end;
    const isTrialActive = status === "trial" && trialEnd && new Date(trialEnd) > new Date();

    return {
      subscription_status: status,
      trial_ends_at: trialEnd,
      stripe_customer_id: org?.stripe_customer_id || null,
      isTrialActive,
      canGenerate: status === "active" || isTrialActive,
    };
  }),
});
