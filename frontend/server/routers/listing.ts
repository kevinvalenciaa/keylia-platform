import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";

const propertyTypeEnum = z.enum([
  "single_family",
  "condo",
  "townhouse",
  "multi_family",
  "land",
]);

const listingStatusEnum = z.enum(["for_sale", "pending", "sold", "withdrawn", "active"]);

// Helper to get user's organization
async function getUserOrganization(supabase: any, userId: string) {
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
async function getListingPhotos(supabase: any, listingId: string): Promise<string[]> {
  const { data: mediaAssets } = await supabase
    .from("media_assets")
    .select("storage_url")
    .like("storage_key", `%${listingId}%`)
    .eq("file_type", "image")
    .order("created_at", { ascending: true });

  return (mediaAssets || []).map((m: any) => m.storage_url);
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

      // Map backend schema to frontend expected format
      const listings = (data || []).map((p: any) => ({
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

      const { data, error } = await ctx.supabase
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
        photos,
        created_at: data.created_at,
        updated_at: data.updated_at,
      };
    }),

  create: protectedProcedure
    .input(
      z.object({
        address: z.string().min(1),
        city: z.string().min(1),
        state: z.string().min(1),
        zip: z.string().min(1),
        price: z.number().positive(),
        bedrooms: z.number().int().min(0),
        bathrooms: z.number().min(0),
        sqft: z.number().int().positive(),
        property_type: propertyTypeEnum,
        status: listingStatusEnum.default("for_sale"),
        description: z.string().optional(),
        features: z.array(z.string()).default([]),
        photos: z.array(z.string().url()).default([]),
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

      const { data, error } = await ctx.supabase
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

        const { error: mediaError } = await ctx.supabase
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
        address: z.string().min(1).optional(),
        city: z.string().min(1).optional(),
        state: z.string().min(1).optional(),
        zip: z.string().min(1).optional(),
        price: z.number().positive().optional(),
        bedrooms: z.number().int().min(0).optional(),
        bathrooms: z.number().min(0).optional(),
        sqft: z.number().int().positive().optional(),
        property_type: propertyTypeEnum.optional(),
        status: listingStatusEnum.optional(),
        description: z.string().nullable().optional(),
        features: z.array(z.string()).optional(),
        photos: z.array(z.string().url()).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Listing not found" });
      }

      const { id, address, city, state, zip, price, bedrooms, bathrooms, sqft, property_type, status, description, features } = input;

      const updates: any = {};
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
      updates.updated_at = new Date().toISOString();

      const { data, error } = await ctx.supabase
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
        photos: [],
        created_at: data.created_at,
        updated_at: data.updated_at,
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
        photos: z.array(z.string().url()),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Photos are stored in media_assets in backend schema
      // For now, return success - full implementation would create media_assets
      return { success: true, message: "Photos should be uploaded via media API" };
    }),
});
