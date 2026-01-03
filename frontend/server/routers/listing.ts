import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import type { SupabaseClient } from "@supabase/supabase-js";

const propertyTypeEnum = z.enum([
  "single_family",
  "condo",
  "townhouse",
  "multi_family",
  "land",
]);

const listingStatusEnum = z.enum(["for_sale", "pending", "sold", "withdrawn", "active"]);

/**
 * Output schema for listing data - ensures consistent types across API.
 * This schema is used to properly type the router outputs.
 */
const listingOutputSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  address: z.string(),
  city: z.string(),
  state: z.string(),
  zip: z.string(),
  price: z.number(),
  bedrooms: z.number(),
  bathrooms: z.number(),
  sqft: z.number(),
  property_type: z.string(),
  status: z.string(),
  description: z.string().nullable(),
  features: z.array(z.string()),
  photos: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
});

/** Type export for client-side usage */
export type ListingOutput = z.infer<typeof listingOutputSchema>;

/** List response schema */
const listResponseSchema = z.object({
  listings: z.array(listingOutputSchema),
  total: z.number(),
});

/** Type for list response */
export type ListingsResponse = z.infer<typeof listResponseSchema>;

// Helper to get user's organization
async function getUserOrganization(supabase: SupabaseClient, userId: string) {
  // First get the user from users table by supabase_id
  const { data: user, error: userError } = await supabase
    .from("users")
    .select("id, supabase_id, email")
    .eq("supabase_id", userId)
    .single();

  if (userError || !user) {
    return null;
  }

  // Get user's organization membership
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

// Helper to fetch photos from media_assets for a listing
// Note: listingId is validated as UUID by zod, so SQL injection is prevented
async function getListingPhotos(supabase: SupabaseClient, listingId: string): Promise<string[]> {
  // Escape special SQL LIKE characters for defense in depth
  // Even though listingId is UUID-validated, this protects against future changes
  const safeListingId = listingId.replace(/[%_\\]/g, "\\$&");

  const { data: mediaAssets } = await supabase
    .from("media_assets")
    .select("storage_url")
    .like("storage_key", `%${safeListingId}%`)
    .eq("file_type", "image")
    .order("created_at", { ascending: true });

  interface MediaAssetRow {
    storage_url: string | null;
  }

  return ((mediaAssets || []) as MediaAssetRow[])
    .map((m) => m.storage_url)
    .filter((url): url is string => url !== null);
}

export const listingRouter = createTRPCRouter({
  list: protectedProcedure
    .input(
      z
        .object({
          status: listingStatusEnum.optional(),
          limit: z.number().min(1).max(100).default(20),
          offset: z.number().min(0).default(0),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        return { listings: [], total: 0 };
      }

      let query = ctx.supabase
        .from("property_listings")
        .select("*", { count: "exact" })
        .eq("organization_id", org.organizationId)
        .order("created_at", { ascending: false })
        .range(input?.offset ?? 0, (input?.offset ?? 0) + (input?.limit ?? 20) - 1);

      if (input?.status) {
        query = query.eq("listing_status", input.status);
      }

      const { data, error, count } = await query;

      if (error) throw error;

      // Database row type from Supabase query
      interface PropertyListingRow {
        id: string;
        address_line1: string;
        city: string;
        state: string;
        zip_code: string | null;
        listing_price: number | null;
        bedrooms: number | null;
        bathrooms: number | null;
        square_feet: number | null;
        property_type: string | null;
        listing_status: string | null;
        positioning_notes: string | null;
        features: string[] | null;
        created_at: string;
        updated_at: string;
      }

      // Map backend schema to frontend expected format with proper typing
      const listings: ListingOutput[] = (data || []).map((p: PropertyListingRow) => ({
        id: p.id,
        user_id: org.dbUserId, // for compatibility
        address: p.address_line1,
        city: p.city,
        state: p.state,
        zip: p.zip_code || "",
        price: p.listing_price || 0,
        bedrooms: p.bedrooms || 0,
        bathrooms: p.bathrooms || 0,
        sqft: p.square_feet || 0,
        property_type: p.property_type || "single_family",
        status: p.listing_status || "active",
        description: p.positioning_notes,
        features: p.features || [],
        photos: [], // Backend stores photos in media_assets
        created_at: p.created_at,
        updated_at: p.updated_at,
      }));

      return { listings, total: count ?? 0 };
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("property_listings")
        .select("*")
        .eq("id", input.id)
        .eq("organization_id", org.organizationId)
        .single();

      if (error?.code === "PGRST116") {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }
      if (error) throw error;

      // Fetch photos from media_assets
      const photos = await getListingPhotos(ctx.supabase, input.id);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const listing = data as any;

      // Map to frontend format
      return {
        id: listing.id,
        user_id: org.dbUserId,
        address: listing.address_line1,
        city: listing.city,
        state: listing.state,
        zip: listing.zip_code || "",
        price: listing.listing_price || 0,
        bedrooms: listing.bedrooms || 0,
        bathrooms: listing.bathrooms || 0,
        sqft: listing.square_feet || 0,
        property_type: listing.property_type || "single_family",
        status: listing.listing_status || "active",
        description: listing.positioning_notes,
        features: listing.features || [],
        photos,
        created_at: listing.created_at,
        updated_at: listing.updated_at,
      };
    }),

  create: protectedProcedure
    .input(
      z.object({
        // Address fields with reasonable max lengths to prevent DoS/storage attacks
        address: z.string().min(1).max(500),
        city: z.string().min(1).max(100),
        state: z.string().min(1).max(50),
        zip: z.string().min(1).max(20),
        // Price with reasonable bounds (max ~$1 trillion)
        price: z.number().positive().max(999999999999),
        bedrooms: z.number().int().min(0).max(100),
        bathrooms: z.number().min(0).max(100),
        sqft: z.number().int().positive().max(10000000), // Max 10M sqft
        property_type: propertyTypeEnum,
        status: listingStatusEnum.default("for_sale"),
        // Description with reasonable max length for rich text
        description: z.string().max(10000).optional(),
        // Features: max 50 features, each max 100 chars
        features: z.array(z.string().max(100)).max(50).default([]),
        // Photos: max 100 photos, validated URLs with max length
        photos: z.array(z.string().url().max(2048)).max(100).default([]),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "No organization found. Please complete onboarding."
        });
      }

      const listingId = crypto.randomUUID();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("property_listings")
        .insert({
          id: listingId,
          organization_id: org.organizationId,
          address_line1: input.address,
          city: input.city,
          state: input.state,
          zip_code: input.zip,
          listing_price: input.price,
          bedrooms: input.bedrooms,
          bathrooms: input.bathrooms,
          square_feet: input.sqft,
          property_type: input.property_type,
          listing_status: input.status === "active" ? "for_sale" : input.status,
          positioning_notes: input.description,
          features: input.features,
        })
        .select()
        .single();

      if (error) throw error;

      // Save photos as media_assets so they can be found by the video generator
      if (input.photos && input.photos.length > 0) {
        const mediaAssets = input.photos.map((url, index) => ({
          id: crypto.randomUUID(),
          organization_id: org.organizationId,
          filename: `listing-${listingId}-photo-${index}.jpg`,
          file_type: "image",
          mime_type: "image/jpeg",
          file_size_bytes: 0,
          storage_key: `listings/${listingId}/photo-${index}`,
          storage_url: url,
          processing_status: "completed",
        }));

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: mediaError } = await (ctx.supabase as any)
          .from("media_assets")
          .insert(mediaAssets)
          .select();

        if (mediaError) {
          // Don't throw - listing was created, just photos weren't linked
        }
      }

      // Map to frontend format
      return {
        id: data.id,
        user_id: org.dbUserId,
        address: data.address_line1,
        city: data.city,
        state: data.state,
        zip: data.zip_code || "",
        price: data.listing_price || 0,
        bedrooms: data.bedrooms || 0,
        bathrooms: data.bathrooms || 0,
        sqft: data.square_feet || 0,
        property_type: data.property_type || "single_family",
        status: data.listing_status || "active",
        description: data.positioning_notes,
        features: data.features || [],
        photos: input.photos || [],
        created_at: data.created_at,
        updated_at: data.updated_at,
      };
    }),

  update: protectedProcedure
    .input(
      z.object({
        id: z.string().uuid(),
        // Same validation as create - max lengths to prevent DoS/storage attacks
        address: z.string().min(1).max(500).optional(),
        city: z.string().min(1).max(100).optional(),
        state: z.string().min(1).max(50).optional(),
        zip: z.string().min(1).max(20).optional(),
        price: z.number().positive().max(999999999999).optional(),
        bedrooms: z.number().int().min(0).max(100).optional(),
        bathrooms: z.number().min(0).max(100).optional(),
        sqft: z.number().int().positive().max(10000000).optional(),
        property_type: propertyTypeEnum.optional(),
        status: listingStatusEnum.optional(),
        description: z.string().max(10000).nullable().optional(),
        features: z.array(z.string().max(100)).max(50).optional(),
        photos: z.array(z.string().url().max(2048)).max(100).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }

      const { id, address, city, state, zip, price, bedrooms, bathrooms, sqft, property_type, status, description, features } = input;

      const updates: {
        address_line1?: string;
        city?: string;
        state?: string;
        zip_code?: string;
        listing_price?: number;
        bedrooms?: number;
        bathrooms?: number;
        square_feet?: number;
        property_type?: string;
        listing_status?: string;
        positioning_notes?: string | null;
        features?: string[];
        updated_at: string;
      } = {
        updated_at: new Date().toISOString(),
      };
      if (address !== undefined) updates.address_line1 = address;
      if (city !== undefined) updates.city = city;
      if (state !== undefined) updates.state = state;
      if (zip !== undefined) updates.zip_code = zip;
      if (price !== undefined) updates.listing_price = price;
      if (bedrooms !== undefined) updates.bedrooms = bedrooms;
      if (bathrooms !== undefined) updates.bathrooms = bathrooms;
      if (sqft !== undefined) updates.square_feet = sqft;
      if (property_type !== undefined) updates.property_type = property_type;
      if (status !== undefined) updates.listing_status = status === "active" ? "for_sale" : status;
      if (description !== undefined) updates.positioning_notes = description;
      if (features !== undefined) updates.features = features;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (ctx.supabase as any)
        .from("property_listings")
        .update(updates)
        .eq("id", id)
        .eq("organization_id", org.organizationId)
        .select()
        .single();

      if (error?.code === "PGRST116") {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }
      if (error) throw error;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const listing = data as any;

      return {
        id: listing.id,
        user_id: org.dbUserId,
        address: listing.address_line1,
        city: listing.city,
        state: listing.state,
        zip: listing.zip_code || "",
        price: listing.listing_price || 0,
        bedrooms: listing.bedrooms || 0,
        bathrooms: listing.bathrooms || 0,
        sqft: listing.square_feet || 0,
        property_type: listing.property_type || "single_family",
        status: listing.listing_status || "active",
        description: listing.positioning_notes,
        features: listing.features || [],
        photos: [],
        created_at: listing.created_at,
        updated_at: listing.updated_at,
      };
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }

      const { error } = await ctx.supabase
        .from("property_listings")
        .delete()
        .eq("id", input.id)
        .eq("organization_id", org.organizationId);

      if (error) throw error;
      return { success: true };
    }),

  addPhotos: protectedProcedure
    .input(
      z.object({
        id: z.string().uuid(),
        // Validate photo URLs with length limits
        photos: z.array(z.string().url().max(2048)).max(100),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Photos are stored in media_assets in backend schema
      // For now, return success - full implementation would create media_assets
      return { success: true, message: "Photos should be uploaded via media API" };
    }),
});
