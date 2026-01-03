import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Helper to get user's organization
async function getUserOrganization(supabase: any, userId: string) {
  const { data: user, error: userError } = await supabase
    .from("users")
    .select("id, full_name")
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
    organizationId: membership.organization_id,
    fullName: user.full_name
  };
}

// Type definitions for Supabase queries
interface ListingData {
  address_line1: string;
  city: string;
  state: string;
  zip_code: string;
  listing_price: number;
  bedrooms: number;
  bathrooms: number;
  square_feet: number;
  property_type: string;
  features: string[] | null;
  positioning_notes: string | null;
}

interface ProjectData {
  type: string;
  generated_caption: string | null;
  property_listings: ListingData | null;
}

const contentTypeEnum = z.enum([
  "just_listed",
  "just_sold",
  "open_house",
  "price_drop",
  "coming_soon",
]);

const platformEnum = z.enum(["instagram", "facebook", "twitter"]);

const PLATFORM_GUIDELINES: Record<string, { maxLength: string; hashtagCount: string; tone: string; format: string }> = {
  instagram: {
    maxLength: "150-200 words",
    hashtagCount: "15-20 relevant hashtags",
    tone: "Storytelling, lifestyle-focused, emoji-friendly. Use line breaks for readability.",
    format: "Start with a hook, tell a story about the property lifestyle, end with a clear CTA",
  },
  facebook: {
    maxLength: "80-120 words",
    hashtagCount: "3-5 hashtags only",
    tone: "Conversational and community-focused. Speak like you're talking to a neighbor.",
    format: "Friendly intro, key highlights, invitation to learn more",
  },
  twitter: {
    maxLength: "280 characters MAX (this is critical - count carefully)",
    hashtagCount: "1-2 hashtags maximum",
    tone: "Punchy, urgent, attention-grabbing. No fluff.",
    format: "Hook + key detail + CTA, all in one tight sentence",
  },
};

export const aiRouter = createTRPCRouter({
  generateContent: protectedProcedure
    .input(
      z.object({
        listing_id: z.string().uuid(),
        content_type: contentTypeEnum,
        platform: platformEnum.default("instagram"),
        additional_context: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Get user's organization
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "No organization found",
        });
      }

      // Get listing data
      const { data: listingData, error: listingError } = await ctx.supabase
        .from("property_listings")
        .select("*")
        .eq("id", input.listing_id)
        .eq("organization_id", org.organizationId)
        .single();

      if (listingError || !listingData) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Listing not found",
        });
      }

      const listing = listingData as ListingData;

      // Build the prompt
      const contentTypeLabels: Record<string, string> = {
        just_listed: "Just Listed",
        just_sold: "Just Sold",
        open_house: "Open House",
        price_drop: "Price Reduction",
        coming_soon: "Coming Soon",
      };

      const platformLabels: Record<string, string> = {
        instagram: "Instagram",
        facebook: "Facebook",
        twitter: "X (Twitter)",
      };

      const guidelines = PLATFORM_GUIDELINES[input.platform];

      const prompt = `You are a real estate social media copywriter specializing in ${platformLabels[input.platform]}. Generate engaging content for this ${contentTypeLabels[input.content_type]} post.

=== PROPERTY INFO ===
Address: ${listing.address_line1}, ${listing.city}, ${listing.state} ${listing.zip_code || ""}
Price: $${(listing.listing_price || 0).toLocaleString()}
Details: ${listing.bedrooms || 0}bd/${listing.bathrooms || 0}ba, ${(listing.square_feet || 0).toLocaleString()} sqft
Type: ${(listing.property_type || "home").replace("_", " ")}
${listing.features?.length ? `Key Features: ${listing.features.join(", ")}` : ""}
${listing.positioning_notes ? `Description: ${listing.positioning_notes}` : ""}
Agent: ${org.fullName || "Real Estate Agent"}
${input.additional_context ? `Additional context: ${input.additional_context}` : ""}

=== PLATFORM REQUIREMENTS (${platformLabels[input.platform]}) ===
- Caption Length: ${guidelines.maxLength}
- Hashtags: ${guidelines.hashtagCount}
- Tone: ${guidelines.tone}
- Format: ${guidelines.format}

=== GENERATE ===
1. Headline: Attention-grabbing (max 8 words)
2. Caption: Follow the platform requirements EXACTLY
3. Hashtags: Follow the count specified above

IMPORTANT: For Twitter, the caption MUST be under 280 characters total. Count carefully!

Respond in JSON format only:
{
  "headline": "string",
  "caption": "string",
  "hashtags": ["string"]
}`;

      try {
        const response = await anthropic.messages.create({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1024,
          messages: [
            {
              role: "user",
              content: prompt,
            },
          ],
        });

        // Extract text content
        const textContent = response.content.find((c) => c.type === "text");
        if (!textContent || textContent.type !== "text") {
          throw new Error("No text content in response");
        }

        // Parse JSON from response
        const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
          throw new Error("Could not parse JSON from response");
        }

        const generated = JSON.parse(jsonMatch[0]) as {
          headline: string;
          caption: string;
          hashtags: string[];
        };

        return {
          headline: generated.headline,
          caption: generated.caption,
          hashtags: generated.hashtags,
          listing_id: input.listing_id,
          content_type: input.content_type,
          platform: input.platform,
        };
      } catch (error) {
        console.error("AI generation error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to generate content. Please try again.",
        });
      }
    }),

  generateDescription: protectedProcedure
    .input(
      z.object({
        address: z.string(),
        city: z.string(),
        state: z.string(),
        price: z.number(),
        bedrooms: z.number(),
        bathrooms: z.number(),
        sqft: z.number(),
        property_type: z.string(),
        features: z.array(z.string()).optional(),
      })
    )
    .mutation(async ({ input }) => {
      const prompt = `Generate a compelling property description for this listing:

Address: ${input.address}, ${input.city}, ${input.state}
Price: $${input.price.toLocaleString()}
Details: ${input.bedrooms}bd/${input.bathrooms}ba, ${input.sqft.toLocaleString()} sqft
Property Type: ${input.property_type.replace("_", " ")}
${input.features?.length ? `Features: ${input.features.join(", ")}` : ""}

Write a 2-3 paragraph property description that:
- Highlights the best features and lifestyle benefits
- Uses vivid, appealing language
- Avoids clichés and generic phrases
- Is professional yet engaging

Also extract 5-8 key features from the context (things like: renovated kitchen, hardwood floors, mountain views, etc.)

Respond in JSON format:
{
  "description": "string",
  "extracted_features": ["string"]
}`;

      try {
        const response = await anthropic.messages.create({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1024,
          messages: [
            {
              role: "user",
              content: prompt,
            },
          ],
        });

        const textContent = response.content.find((c) => c.type === "text");
        if (!textContent || textContent.type !== "text") {
          throw new Error("No text content in response");
        }

        const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
          throw new Error("Could not parse JSON from response");
        }

        const generated = JSON.parse(jsonMatch[0]) as {
          description: string;
          extracted_features: string[];
        };

        return generated;
      } catch (error) {
        console.error("AI generation error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to generate description. Please try again.",
        });
      }
    }),

  regenerateCaption: protectedProcedure
    .input(
      z.object({
        content_id: z.string().uuid(),
        feedback: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Get user's organization
      const org = await getUserOrganization(ctx.supabase, ctx.user.id);
      if (!org) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "No organization found",
        });
      }

      // Get existing project with property listing
      const { data: projectData, error } = await ctx.supabase
        .from("projects")
        .select("*, property_listings(*)")
        .eq("id", input.content_id)
        .eq("organization_id", org.organizationId)
        .single();

      if (error || !projectData) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Content not found",
        });
      }

      const project = projectData as ProjectData;
      const listing = project.property_listings as ListingData;

      const prompt = `Regenerate the Instagram caption for this real estate post.

Property: ${listing.address_line1}, ${listing.city}, ${listing.state}
Price: $${(listing.listing_price || 0).toLocaleString()}
Details: ${listing.bedrooms || 0}bd/${listing.bathrooms || 0}ba, ${(listing.square_feet || 0).toLocaleString()} sqft
Content Type: ${project.type}
Current Caption: ${project.generated_caption}
${input.feedback ? `User Feedback: ${input.feedback}` : "Make it different and fresh"}

Generate a new caption (150-200 words) and updated hashtags. Make it different from the current one while maintaining professionalism.

Respond in JSON format:
{
  "caption": "string",
  "hashtags": ["string"]
}`;

      try {
        const response = await anthropic.messages.create({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1024,
          messages: [
            {
              role: "user",
              content: prompt,
            },
          ],
        });

        const textContent = response.content.find((c) => c.type === "text");
        if (!textContent || textContent.type !== "text") {
          throw new Error("No text content in response");
        }

        const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
          throw new Error("Could not parse JSON from response");
        }

        const generated = JSON.parse(jsonMatch[0]) as {
          caption: string;
          hashtags: string[];
        };

        // Update the project
        const { data: updated, error: updateError } = await ctx.supabase
          .from("projects")
          .update({
            generated_caption: generated.caption,
            generated_hashtags: generated.hashtags,
            updated_at: new Date().toISOString(),
          })
          .eq("id", input.content_id)
          .eq("organization_id", org.organizationId)
          .select()
          .single();

        if (updateError) throw updateError;

        return {
          id: updated.id,
          caption: updated.generated_caption,
          hashtags: updated.generated_hashtags,
        };
      } catch (error) {
        console.error("AI regeneration error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to regenerate content. Please try again.",
        });
      }
    }),
});
