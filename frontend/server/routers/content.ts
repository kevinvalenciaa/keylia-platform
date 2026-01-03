import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";

const contentTypeEnum = z.enum([
  "just_listed",
  "just_sold",
  "open_house",
  "price_drop",
  "coming_soon",
]);

const formatEnum = z.enum(["square", "portrait", "story"]);
const statusEnum = z.enum(["draft", "downloaded", "published"]);

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

// Map backend project types to frontend content types
const projectTypeToContentType: Record<string, string> = {
  "listing_video": "just_listed",
  "listing_tour": "just_listed",
  "sold_video": "just_sold",
  "open_house_video": "open_house",
};

const contentTypeToProjectType: Record<string, string> = {
  "just_listed": "listing_video",
  "just_sold": "sold_video",
  "open_house": "open_house_video",
  "price_drop": "listing_video",
  "coming_soon": "listing_video",
};

export const contentRouter = createTRPCRouter({
  list: protectedProcedure
    .input(
      z
        .object({
          listing_id: z.string().uuid().optional(),
          content_type: contentTypeEnum.optional(),
          status: statusEnum.optional(),
          limit: z.number().min(1).max(100).default(20),
          offset: z.number().min(0).default(0),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        return { content: [], total: 0 };
      }

      let query = ctx.supabase
        .from("projects")
        .select("*, property_listings(address_line1, city, state, listing_price), render_jobs(output_url, status)", { count: "exact" })
        .eq("organization_id", org.organizationId)
        .order("created_at", { ascending: false })
        .range(input?.offset ?? 0, (input?.offset ?? 0) + (input?.limit ?? 20) - 1);

      if (input?.listing_id) {
        query = query.eq("property_id", input.listing_id);
      }
      if (input?.content_type) {
        const projectType = contentTypeToProjectType[input.content_type] || input.content_type;
        query = query.eq("type", projectType);
      }
      if (input?.status) {
        query = query.eq("status", input.status);
      }

      const { data, error, count } = await query;

      if (error) throw error;

      // Map projects to content format
      const content = (data || []).map((p: any) => {
        // Get the video URL from completed render jobs
        const renderJobs = p.render_jobs || [];
        const completedJob = renderJobs.find((job: any) => job.status === "completed" && job.output_url);
        const videoUrl = completedJob?.output_url || null;

        return {
          id: p.id,
          user_id: org.dbUserId,
          listing_id: p.property_id,
          content_type: projectTypeToContentType[p.type] || "just_listed",
          format: "square" as const,
          caption: p.generated_caption,
          hashtags: p.generated_hashtags || [],
          image_url: null,
          video_url: videoUrl,
          status: p.status,
          download_count: 0,
          created_at: p.created_at,
          updated_at: p.updated_at,
          // Include listing info
          listings: p.property_listings ? {
            address: p.property_listings.address_line1,
            city: p.property_listings.city,
            state: p.property_listings.state,
            price: p.property_listings.listing_price,
          } : null,
        };
      });

      return { content, total: count ?? 0 };
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Content not found" });
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("projects")
        .select("*, property_listings(*), render_jobs(output_url, status)")
        .eq("id", input.id)
        .eq("organization_id", org.organizationId)
        .single();

      if (error?.code === "PGRST116") {
        throw new TRPCError({ code: "NOT_FOUND", message: "Content not found" });
      }
      if (error) throw error;

      // Get the video URL from completed render jobs
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const renderJobs = (data as any).render_jobs || [];
      const completedJob = renderJobs.find((job: any) => job.status === "completed" && job.output_url);
      const videoUrl = completedJob?.output_url || null;

      return {
        id: data.id,
        user_id: org.dbUserId,
        listing_id: data.property_id,
        content_type: projectTypeToContentType[data.type] || "just_listed",
        format: "square" as const,
        caption: data.generated_caption,
        hashtags: data.generated_hashtags || [],
        image_url: null,
        video_url: videoUrl,
        status: data.status,
        download_count: 0,
        created_at: data.created_at,
        updated_at: data.updated_at,
        listings: data.property_listings,
      };
    }),

  create: protectedProcedure
    .input(
      z.object({
        listing_id: z.string().uuid(),
        content_type: contentTypeEnum,
        format: formatEnum.default("square"),
        caption: z.string().optional(),
        hashtags: z.array(z.string()).default([]),
        image_url: z.string().url().optional(),
        template_id: z.string().uuid().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "No organization found",
        });
      }

      // Verify listing exists and belongs to org
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: listingData, error: listingError } = await (ctx.supabase as any)
        .from("property_listings")
        .select("id, address_line1")
        .eq("id", input.listing_id)
        .eq("organization_id", org.organizationId)
        .single();

      const listing = listingData as { id: string; address_line1: string } | null;

      if (listingError || !listing) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Listing not found",
        });
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("projects")
        .insert({
          organization_id: org.organizationId,
          created_by_id: org.dbUserId,
          property_id: input.listing_id,
          title: `${input.content_type} - ${listing.address_line1}`,
          type: contentTypeToProjectType[input.content_type] || "listing_video",
          status: "draft",
          generated_caption: input.caption,
          generated_hashtags: input.hashtags,
          style_settings: { format: input.format },
          voice_settings: {},
          infographic_settings: {},
        })
        .select()
        .single();

      if (error) throw error;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const projectData = data as any;

      return {
        id: projectData.id,
        user_id: org.dbUserId,
        listing_id: projectData.property_id,
        content_type: input.content_type,
        format: input.format,
        caption: projectData.generated_caption,
        hashtags: projectData.generated_hashtags || [],
        image_url: null,
        status: projectData.status,
        download_count: 0,
        created_at: projectData.created_at,
        updated_at: projectData.updated_at,
      };
    }),

  update: protectedProcedure
    .input(
      z.object({
        id: z.string().uuid(),
        caption: z.string().nullable().optional(),
        hashtags: z.array(z.string()).optional(),
        image_url: z.string().url().nullable().optional(),
        template_id: z.string().uuid().nullable().optional(),
        status: statusEnum.optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Content not found" });
      }

      const { id, caption, hashtags, status } = input;

      const updates: any = {};
      if (caption !== undefined) updates.generated_caption = caption;
      if (hashtags !== undefined) updates.generated_hashtags = hashtags;
      if (status !== undefined) updates.status = status;
      updates.updated_at = new Date().toISOString();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("projects")
        .update(updates)
        .eq("id", id)
        .eq("organization_id", org.organizationId)
        .select()
        .single();

      if (error?.code === "PGRST116") {
        throw new TRPCError({ code: "NOT_FOUND", message: "Content not found" });
      }
      if (error) throw error;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const projectData = data as any;

      return {
        id: projectData.id,
        user_id: org.dbUserId,
        listing_id: projectData.property_id,
        content_type: projectTypeToContentType[projectData.type] || "just_listed",
        format: "square" as const,
        caption: projectData.generated_caption,
        hashtags: projectData.generated_hashtags || [],
        image_url: null,
        status: projectData.status,
        download_count: 0,
        created_at: projectData.created_at,
        updated_at: projectData.updated_at,
      };
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Content not found" });
      }

      // Delete related render jobs first (foreign key constraint)
      const { error: renderJobsError } = await ctx.supabase
        .from("render_jobs")
        .delete()
        .eq("project_id", input.id);

      if (renderJobsError) throw renderJobsError;

      // Now delete the project
      const { error } = await ctx.supabase
        .from("projects")
        .delete()
        .eq("id", input.id)
        .eq("organization_id", org.organizationId);

      if (error) throw error;
      return { success: true };
    }),

  trackDownload: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      // Downloads are tracked differently in backend schema
      // For now, just return success
      return { success: true };
    }),

  getStats: protectedProcedure.query(async ({ ctx }) => {
    const org = await getUserOrganization(ctx.supabase, ctx.user.id);
    if (!org) {
      return {
        total: 0,
        drafts: 0,
        downloaded: 0,
        published: 0,
        totalDownloads: 0,
      };
    }

    const { data, error } = await ctx.supabase
      .from("projects")
      .select("status")
      .eq("organization_id", org.organizationId);

    if (error) throw error;

    const projects = data || [];
    const stats = {
      total: projects.length,
      drafts: projects.filter((p: any) => p.status === "draft").length,
      downloaded: projects.filter((p: any) => p.status === "downloaded").length,
      published: projects.filter((p: any) => p.status === "published" || p.status === "completed").length,
      totalDownloads: 0, // Backend tracks this differently
    };

    return stats;
  }),
});
