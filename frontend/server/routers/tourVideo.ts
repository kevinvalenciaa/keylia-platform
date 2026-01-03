import { z } from "zod";
import { createTRPCRouter, protectedProcedure, publicProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";

const voiceSettingsSchema = z.object({
  voice_id: z.string().optional(),
  language: z.string().default("en-US"),
  style: z.string().default("professional"),
  gender: z.enum(["male", "female"]).default("female"),
});

const styleSettingsSchema = z.object({
  tone: z.enum(["luxury", "cozy", "modern", "minimal", "bold"]).default("modern"),
  pace: z.enum(["slow", "moderate", "fast"]).default("moderate"),
  music_style: z.string().optional(),
  video_model: z.enum(["kling", "kling_pro", "kling_v2", "veo3", "veo3_fast", "minimax", "runway"]).default("kling"),
});

const durationEnum = z.enum(["15", "30", "60"]);

export const tourVideoRouter = createTRPCRouter({
  // Generate tour video from a listing
  generateFromListing: protectedProcedure
    .input(
      z.object({
        listingId: z.string().uuid(),
        duration: durationEnum.default("30"),
        voiceSettings: voiceSettingsSchema.optional(),
        styleSettings: styleSettingsSchema.optional(),
        brandKitId: z.string().uuid().optional(),
        photoOrder: z.array(z.string().uuid()).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Call backend API to start video generation
      // Backend handles ownership verification through organization membership
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        throw new TRPCError({
          code: "UNAUTHORIZED",
          message: "Not authenticated",
        });
      }

      const response = await fetch(
        `${API_URL}/api/v1/tour-videos/from-listing/${input.listingId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            duration_seconds: parseInt(input.duration),
            voice_settings: input.voiceSettings || {},
            style_settings: input.styleSettings || {},
            brand_kit_id: input.brandKitId,
            photo_order: input.photoOrder,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to start video generation" }));
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: error.detail || "Failed to start video generation",
        });
      }

      const result = await response.json();
      return {
        projectId: result.project_id,
        renderJobId: result.render_job_id,
        status: result.status,
        message: result.message,
      };
    }),

  // Get video generation progress
  getProgress: protectedProcedure
    .input(z.object({ projectId: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(
        `${API_URL}/api/v1/tour-videos/${input.projectId}/progress`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Project not found",
        });
      }

      const result = await response.json();
      return {
        projectId: result.project_id,
        renderJobId: result.render_job_id,
        status: result.status,
        progressPercent: result.progress_percent,
        currentStep: result.current_step,
        stepDetails: result.step_details,
        estimatedRemainingSeconds: result.estimated_remaining_seconds,
        outputUrl: result.output_url,
        errorMessage: result.error_message,
      };
    }),

  // Get video preview with scenes
  getPreview: protectedProcedure
    .input(z.object({ projectId: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(
        `${API_URL}/api/v1/tour-videos/${input.projectId}/preview`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Project not found",
        });
      }

      return response.json();
    }),

  // List available voices (public - returns default voices without auth)
  getVoices: publicProcedure.query(async ({ ctx }) => {
    // Default voices - always available as fallback
    const defaultVoices = [
      {
        voiceId: "21m00Tcm4TlvDq8ikWAM",
        name: "Rachel",
        label: "professional_female",
        previewUrl: null,
        category: "premade",
      },
      {
        voiceId: "29vD33N1CtxCmqQRPOHJ",
        name: "Drew",
        label: "professional_male",
        previewUrl: null,
        category: "premade",
      },
      {
        voiceId: "EXAVITQu4vr4xnSDxMaL",
        name: "Bella",
        label: "friendly_female",
        previewUrl: null,
        category: "premade",
      },
      {
        voiceId: "ErXwobaYiN019PkySvjV",
        name: "Antoni",
        label: "warm_male",
        previewUrl: null,
        category: "premade",
      },
    ];

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // Get access token from Supabase session
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      // If no session, return default voices without calling backend
      if (!token) {
        return defaultVoices;
      }

      const response = await fetch(`${API_URL}/api/v1/tour-videos/voices`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        // Return default voices if API fails
        return defaultVoices;
      }

      const voices = await response.json();
      if (!Array.isArray(voices) || voices.length === 0) {
        return defaultVoices;
      }

      return voices.map((v: any) => ({
        voiceId: v.voice_id,
        name: v.name,
        label: v.label,
        previewUrl: v.preview_url,
        category: v.category,
      }));
    } catch (error) {
      // Return default voices on any error (network, parsing, etc.)
      console.error("Failed to fetch voices from backend:", error);
      return defaultVoices;
    }
  }),

  // Cancel video generation
  cancel: protectedProcedure
    .input(z.object({ projectId: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(
        `${API_URL}/api/v1/tour-videos/${input.projectId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to cancel video generation",
        });
      }

      return { success: true };
    }),

  // List tour videos for a listing
  listForListing: protectedProcedure
    .input(z.object({ listingId: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const { data: { session } } = await ctx.supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(
        `${API_URL}/api/v1/projects?type=listing_tour&property_id=${input.listingId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        return { projects: [], total: 0 };
      }

      const result = await response.json();
      return {
        projects: result.projects,
        total: result.total,
      };
    }),
});
