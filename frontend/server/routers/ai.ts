import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import Anthropic from "@anthropic-ai/sdk";
import { circuitBreakers, CircuitBreakerError } from "@/lib/circuit-breaker";
import {
  sanitizeForPrompt,
  sanitizeArrayForPrompt,
  createSafePropertyDescription,
} from "@/lib/sanitization";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Helper to get user's organization
// Note: Using 'any' for supabase because the Database types may not include all tables
// eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    fullName: user.full_name,
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

const PLATFORM_GUIDELINES: Record<
  string,
  { maxLength: string; hashtagCount: string; tone: string; format: string }
> = {
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

/**
 * Call Anthropic API with circuit breaker protection.
 * Handles failures gracefully and prevents cascading failures.
 */
async function callAnthropicWithBreaker(
  prompt: string,
  maxTokens = 1024
): Promise<Anthropic.Message> {
  try {
    return await circuitBreakers.anthropic.call(() =>
      anthropic.messages.create({
        model: "claude-sonnet-4-20250514",
        max_tokens: maxTokens,
        messages: [{ role: "user", content: prompt }],
      })
    );
  } catch (error) {
    if (error instanceof CircuitBreakerError) {
      throw new TRPCError({
        code: "SERVICE_UNAVAILABLE",
        message: "AI service is temporarily unavailable. Please try again in a few minutes.",
        cause: error,
      });
    }
    throw error;
  }
}

/**
 * Parse JSON from AI response with validation.
 */
function parseJsonResponse<T>(response: Anthropic.Message): T {
  const textContent = response.content.find((c) => c.type === "text");
  if (!textContent || textContent.type !== "text") {
    throw new Error("No text content in response");
  }

  const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error("Could not parse JSON from response");
  }

  return JSON.parse(jsonMatch[0]) as T;
}

export const aiRouter = createTRPCRouter({
  generateContent: protectedProcedure
    .input(
      z.object({
        listing_id: z.string().uuid(),
        content_type: contentTypeEnum,
        platform: platformEnum.default("instagram"),
        additional_context: z.string().max(1000).optional(),
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

      // Build the prompt with sanitized data
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

      // Sanitize all user-provided data before including in prompt
      const safePropertyDescription = createSafePropertyDescription(listing);
      const safeAgentName = sanitizeForPrompt(org.fullName, 100) || "Real Estate Agent";
      const safeAdditionalContext = input.additional_context
        ? sanitizeForPrompt(input.additional_context, 1000)
        : "";

      const prompt = `You are a real estate social media copywriter specializing in ${platformLabels[input.platform]}. Generate engaging content for this ${contentTypeLabels[input.content_type]} post.

=== PROPERTY INFO ===
${safePropertyDescription}
Agent: ${safeAgentName}
${safeAdditionalContext ? `Additional context: ${safeAdditionalContext}` : ""}

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
        const response = await callAnthropicWithBreaker(prompt);

        const generated = parseJsonResponse<{
          headline: string;
          caption: string;
          hashtags: string[];
        }>(response);

        return {
          headline: generated.headline,
          caption: generated.caption,
          hashtags: generated.hashtags,
          listing_id: input.listing_id,
          content_type: input.content_type,
          platform: input.platform,
        };
      } catch (error) {
        if (error instanceof TRPCError) throw error;

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
        address: z.string().max(500),
        city: z.string().max(100),
        state: z.string().max(50),
        price: z.number().positive().max(999999999999),
        bedrooms: z.number().int().min(0).max(100),
        bathrooms: z.number().min(0).max(100),
        sqft: z.number().int().positive().max(10000000),
        property_type: z.string().max(50),
        features: z.array(z.string().max(100)).max(50).optional(),
      })
    )
    .mutation(async ({ input }) => {
      // Sanitize all inputs
      const safeAddress = sanitizeForPrompt(input.address, 500);
      const safeCity = sanitizeForPrompt(input.city, 100);
      const safeState = sanitizeForPrompt(input.state, 50);
      const safePropertyType = sanitizeForPrompt(input.property_type, 50);
      const safeFeatures = sanitizeArrayForPrompt(input.features, 50, 100);

      const prompt = `Generate a compelling property description for this listing:

Address: ${safeAddress}, ${safeCity}, ${safeState}
Price: $${input.price.toLocaleString()}
Details: ${input.bedrooms}bd/${input.bathrooms}ba, ${input.sqft.toLocaleString()} sqft
Property Type: ${safePropertyType.replace("_", " ")}
${safeFeatures.length > 0 ? `Features: ${safeFeatures.join(", ")}` : ""}

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
        const response = await callAnthropicWithBreaker(prompt);

        const generated = parseJsonResponse<{
          description: string;
          extracted_features: string[];
        }>(response);

        return generated;
      } catch (error) {
        if (error instanceof TRPCError) throw error;

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
        feedback: z.string().max(500).optional(),
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

      // Sanitize inputs
      const safePropertyDescription = createSafePropertyDescription(listing);
      const safeCurrentCaption = sanitizeForPrompt(project.generated_caption, 2000);
      const safeFeedback = input.feedback
        ? sanitizeForPrompt(input.feedback, 500)
        : "Make it different and fresh";

      const prompt = `Regenerate the Instagram caption for this real estate post.

${safePropertyDescription}
Content Type: ${sanitizeForPrompt(project.type, 50)}
Current Caption: ${safeCurrentCaption}
User Feedback: ${safeFeedback}

Generate a new caption (150-200 words) and updated hashtags. Make it different from the current one while maintaining professionalism.

Respond in JSON format:
{
  "caption": "string",
  "hashtags": ["string"]
}`;

      try {
        const response = await callAnthropicWithBreaker(prompt);

        const generated = parseJsonResponse<{
          caption: string;
          hashtags: string[];
        }>(response);

        // Update the project
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { data: updated, error: updateError } = await (ctx.supabase as any)
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
        if (error instanceof TRPCError) throw error;

        console.error("AI regeneration error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to regenerate content. Please try again.",
        });
      }
    }),

  /**
   * Get AI service health status.
   * Useful for monitoring and debugging.
   */
  getServiceStatus: protectedProcedure.query(() => {
    const stats = circuitBreakers.anthropic.getStats();
    return {
      status: stats.state === "CLOSED" ? "healthy" : stats.state === "HALF_OPEN" ? "recovering" : "degraded",
      circuitState: stats.state,
      totalCalls: stats.totalCalls,
      totalFailures: stats.totalFailures,
      isAvailable: circuitBreakers.anthropic.isAvailable(),
    };
  }),
});
