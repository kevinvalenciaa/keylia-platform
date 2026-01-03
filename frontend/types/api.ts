/**
 * TypeScript types for API requests and responses.
 */

import type { SupabaseClient } from "@supabase/supabase-js";

// Supabase client type for routers
export type SupabaseClientType = SupabaseClient;

// User update input type
export interface UserUpdateInput {
  full_name?: string;
  phone?: string;
  updated_at: string;
}

// Listing update input type
export interface ListingUpdateInput {
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
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  error: ApiError | null;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// Pagination types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface PaginationInput {
  page?: number;
  pageSize?: number;
  offset?: number;
  limit?: number;
}

// Voice types for tour video
export interface Voice {
  voiceId: string;
  name: string;
  label: string;
  previewUrl: string | null;
  category: string;
}

// Tour video generation types
export interface TourVideoGenerationInput {
  listingId: string;
  duration: "15" | "30" | "60";
  voiceSettings?: {
    voice_id?: string;
    language?: string;
    style?: string;
    gender?: "male" | "female";
  };
  styleSettings?: {
    tone?: "luxury" | "cozy" | "modern" | "minimal" | "bold";
    pace?: "slow" | "moderate" | "fast";
    music_style?: string;
    video_model?: string;
  };
  brandKitId?: string;
  photoOrder?: string[];
}

export interface TourVideoProgress {
  projectId: string;
  renderJobId: string | null;
  status: string;
  progressPercent: number;
  currentStep: string | null;
  stepDetails: Record<string, unknown>;
  estimatedRemainingSeconds: number | null;
  outputUrl: string | null;
  errorMessage: string | null;
}

// Listing frontend format
export interface ListingFrontend {
  id: string;
  user_id: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  property_type: string;
  status: string;
  description: string | null;
  features: string[];
  photos: string[];
  created_at: string;
  updated_at: string;
}

// Profile types
export interface UserProfile {
  id: string;
  full_name: string;
  brokerage: string | null;
  phone: string | null;
  subscription_status: "trial" | "active" | "cancelled" | "past_due";
  stripe_customer_id: string | null;
  trial_ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionStatusResponse {
  subscription_status: string;
  trial_ends_at: string | null;
  stripe_customer_id: string | null;
  isTrialActive: boolean;
  canGenerate: boolean;
}

// Content generation types
export interface GeneratedCaption {
  caption: string;
  hashtags: string[];
  platform: string;
}

export interface GeneratedScript {
  hook: string;
  scenes: SceneScript[];
  cta: string;
  caption: string;
  hashtags: string[];
}

export interface SceneScript {
  scene_number: number;
  narration: string;
  on_screen_text?: string;
  camera_movement?: string;
}

// Billing types
export interface CreateCheckoutSessionInput {
  priceId: string;
  successUrl: string;
  cancelUrl: string;
}

export interface CreatePortalSessionInput {
  returnUrl: string;
}
