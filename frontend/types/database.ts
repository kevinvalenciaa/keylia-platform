/**
 * TypeScript types for database entities.
 * These types mirror the backend SQLAlchemy models for type safety.
 */

// Base entity type with common fields
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
}

// User entity
export interface User extends BaseEntity {
  supabase_id: string | null;
  email: string;
  full_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  email_verified: boolean;
  is_active: boolean;
}

// Organization entity
export interface Organization extends BaseEntity {
  name: string;
  slug: string;
  owner_id: string;
  stripe_customer_id: string | null;
  settings: Record<string, unknown>;
}

// Organization member entity
export interface OrganizationMember {
  organization_id: string;
  user_id: string;
  role: "owner" | "admin" | "member";
  joined_at: string;
}

// Property listing entity
export interface PropertyListing extends BaseEntity {
  organization_id: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string;
  zip_code: string | null;
  country: string;
  neighborhood: string | null;
  listing_price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  square_feet: number | null;
  lot_size: number | null;
  year_built: number | null;
  property_type: PropertyType;
  listing_status: ListingStatus;
  mls_number: string | null;
  features: string[];
  positioning_notes: string | null;
  target_audience: string | null;
  open_house_dates: OpenHouseDate[];
}

export type PropertyType =
  | "single_family"
  | "condo"
  | "townhouse"
  | "multi_family"
  | "land"
  | "commercial";

export type ListingStatus =
  | "draft"
  | "for_sale"
  | "pending"
  | "sold"
  | "withdrawn"
  | "active";

export interface OpenHouseDate {
  date: string;
  start_time: string;
  end_time: string;
}

// Project entity
export interface Project extends BaseEntity {
  organization_id: string;
  created_by_id: string;
  property_id: string | null;
  brand_kit_id: string | null;
  title: string;
  type: ProjectType;
  status: ProjectStatus;
  style_settings: StyleSettings;
  voice_settings: VoiceSettings;
  target_platforms: string[];
  generated_script: string | null;
  generated_caption: string | null;
  generated_hashtags: string[];
}

export type ProjectType =
  | "listing_tour"
  | "promo_video"
  | "infographic"
  | "social_post";

export type ProjectStatus =
  | "draft"
  | "script_pending"
  | "script_ready"
  | "rendering"
  | "completed"
  | "failed";

export interface StyleSettings {
  tone?: "luxury" | "cozy" | "modern" | "minimal" | "bold";
  pace?: "slow" | "moderate" | "fast";
  music_style?: string;
  duration_seconds?: number;
  platform?: string;
  aspect_ratio?: string;
  video_model?: VideoModel;
}

export type VideoModel =
  | "kling"
  | "kling_pro"
  | "kling_v2"
  | "veo3"
  | "veo3_fast"
  | "minimax"
  | "runway";

export interface VoiceSettings {
  enabled?: boolean;
  voice_id?: string;
  language?: string;
  style?: string;
  gender?: "male" | "female";
}

// Media asset entity
export interface MediaAsset extends BaseEntity {
  organization_id: string;
  project_id: string | null;
  filename: string;
  file_type: MediaType;
  mime_type: string;
  file_size_bytes: number;
  storage_key: string;
  storage_url: string | null;
  cdn_url: string | null;
  processing_status: ProcessingStatus;
  metadata: MediaMetadata;
}

export type MediaType =
  | "image"
  | "video"
  | "audio"
  | "voiceover"
  | "music"
  | "logo"
  | "headshot";

export type ProcessingStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface MediaMetadata {
  width?: number;
  height?: number;
  duration_seconds?: number;
  thumbnail_url?: string;
}

// Render job entity
export interface RenderJob extends BaseEntity {
  project_id: string;
  status: RenderStatus;
  render_type: RenderType;
  progress_percent: number;
  current_step: string | null;
  step_details: Record<string, unknown>;
  output_url: string | null;
  subtitle_url: string | null;
  thumbnail_url: string | null;
  file_size_bytes: number | null;
  duration_seconds: number | null;
  error_message: string | null;
  error_details: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, unknown>;
}

export type RenderStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled";

export type RenderType = "full" | "preview" | "thumbnail";

// Brand kit entity
export interface BrandKit extends BaseEntity {
  organization_id: string;
  name: string;
  is_default: boolean;
  agent_name: string | null;
  agent_title: string | null;
  brokerage_name: string | null;
  agent_email: string | null;
  agent_phone: string | null;
  headshot_url: string | null;
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  font_heading: string;
  font_body: string;
}

// Subscription entity
export interface Subscription extends BaseEntity {
  organization_id: string;
  stripe_subscription_id: string | null;
  plan_name: SubscriptionPlan;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  trial_end: string | null;
  cancel_at_period_end: boolean;
  video_renders_limit: number;
  ai_generations_limit: number;
  storage_limit_gb: number;
  video_renders_used: number;
  ai_generations_used: number;
  storage_used_bytes: number;
}

export type SubscriptionPlan =
  | "free"
  | "starter"
  | "professional"
  | "team"
  | "enterprise";

export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "incomplete";

// Scene entity
export interface Scene extends BaseEntity {
  project_id: string;
  media_asset_id: string | null;
  sequence_order: number;
  start_time_ms: number;
  duration_ms: number;
  narration_text: string | null;
  on_screen_text: string | null;
  camera_movement: CameraMovement;
  transition_type: TransitionType;
  ai_generated_video_url: string | null;
}

export interface CameraMovement {
  type: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static";
  easing?: string;
}

export type TransitionType =
  | "cut"
  | "crossfade"
  | "fade_black"
  | "fade_white"
  | "slide_left"
  | "slide_right";

// Webhook events for idempotency tracking
export interface WebhookEvent extends BaseEntity {
  stripe_event_id: string;
  event_type: string;
  processed_at: string;
}

/**
 * Supabase Database type definition for type-safe queries.
 * This is a simplified version - for full type safety, generate
 * types using `supabase gen types typescript`.
 */
export interface Database {
  public: {
    Tables: {
      users: {
        Row: User;
        Insert: Omit<User, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<User, "id">>;
      };
      organizations: {
        Row: Organization;
        Insert: Omit<Organization, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<Organization, "id">>;
      };
      organization_members: {
        Row: OrganizationMember;
        Insert: OrganizationMember;
        Update: Partial<OrganizationMember>;
      };
      property_listings: {
        Row: PropertyListing;
        Insert: Omit<PropertyListing, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<PropertyListing, "id">>;
      };
      projects: {
        Row: Project;
        Insert: Omit<Project, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<Project, "id">>;
      };
      media_assets: {
        Row: MediaAsset;
        Insert: Omit<MediaAsset, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<MediaAsset, "id">>;
      };
      render_jobs: {
        Row: RenderJob;
        Insert: Omit<RenderJob, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<RenderJob, "id">>;
      };
      brand_kits: {
        Row: BrandKit;
        Insert: Omit<BrandKit, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<BrandKit, "id">>;
      };
      subscriptions: {
        Row: Subscription;
        Insert: Omit<Subscription, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<Subscription, "id">>;
      };
      scenes: {
        Row: Scene;
        Insert: Omit<Scene, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<Scene, "id">>;
      };
      webhook_events: {
        Row: WebhookEvent;
        Insert: Omit<WebhookEvent, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<WebhookEvent, "id">>;
      };
    };
    Views: Record<string, never>;
    Functions: {
      increment_video_renders_usage: {
        Args: {
          p_organization_id: string;
          p_increment_by?: number;
        };
        Returns: {
          success: boolean;
          new_count: number;
          limit_value: number | null;
          remaining: number | null;
        }[];
      };
    };
    Enums: Record<string, never>;
  };
}
