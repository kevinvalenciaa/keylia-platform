-- =============================================================================
-- ReelAgent MVP Schema (Simplified)
-- =============================================================================
-- This is the simplified MVP schema. Run this on a fresh Supabase project.
--
-- NOTE: If you have the old complex schema, you'll need to either:
-- 1. Create a new Supabase project
-- 2. Or manually drop all existing tables and run this
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- PROFILES TABLE (extends Supabase auth.users)
-- =============================================================================
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  brokerage TEXT,
  phone TEXT,
  subscription_status TEXT DEFAULT 'trial' CHECK (subscription_status IN ('trial', 'active', 'cancelled', 'past_due')),
  stripe_customer_id TEXT UNIQUE,
  trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_subscription ON profiles(subscription_status);
CREATE INDEX IF NOT EXISTS idx_profiles_stripe ON profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- =============================================================================
-- BRAND KITS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS brand_kits (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  logo_url TEXT,
  primary_color TEXT DEFAULT '#1a1a2e',
  secondary_color TEXT DEFAULT '#4a5568',
  font_family TEXT DEFAULT 'Inter',
  tagline TEXT,
  contact_info JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_brand_kits_user ON brand_kits(user_id);

-- =============================================================================
-- LISTINGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS listings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  zip TEXT NOT NULL,
  price INTEGER NOT NULL,
  bedrooms INTEGER NOT NULL DEFAULT 0,
  bathrooms NUMERIC NOT NULL DEFAULT 0,
  sqft INTEGER NOT NULL DEFAULT 0,
  property_type TEXT NOT NULL DEFAULT 'single_family' CHECK (property_type IN ('single_family', 'condo', 'townhouse', 'multi_family', 'land')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'pending', 'sold', 'withdrawn')),
  description TEXT,
  features TEXT[] DEFAULT '{}',
  photos TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_listings_user ON listings(user_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC);

-- =============================================================================
-- TEMPLATES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('listing', 'educational', 'personal')),
  thumbnail_url TEXT,
  layout_config JSONB NOT NULL DEFAULT '{}',
  is_premium BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_premium ON templates(is_premium);

-- =============================================================================
-- CONTENT PIECES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_pieces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  content_type TEXT NOT NULL CHECK (content_type IN ('just_listed', 'just_sold', 'open_house', 'price_drop', 'coming_soon')),
  format TEXT DEFAULT 'square' CHECK (format IN ('square', 'portrait', 'story')),
  caption TEXT,
  hashtags TEXT[] DEFAULT '{}',
  image_url TEXT,
  template_id UUID REFERENCES templates(id) ON DELETE SET NULL,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'downloaded', 'published')),
  download_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_user ON content_pieces(user_id);
CREATE INDEX IF NOT EXISTS idx_content_listing ON content_pieces(listing_id);
CREATE INDEX IF NOT EXISTS idx_content_status ON content_pieces(status);
CREATE INDEX IF NOT EXISTS idx_content_created ON content_pieces(created_at DESC);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_kits ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_pieces ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

-- Brand kits policies
CREATE POLICY "Users can view own brand kit" ON brand_kits
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own brand kit" ON brand_kits
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own brand kit" ON brand_kits
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own brand kit" ON brand_kits
  FOR DELETE USING (auth.uid() = user_id);

-- Listings policies
CREATE POLICY "Users can view own listings" ON listings
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own listings" ON listings
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own listings" ON listings
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own listings" ON listings
  FOR DELETE USING (auth.uid() = user_id);

-- Content pieces policies
CREATE POLICY "Users can view own content" ON content_pieces
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own content" ON content_pieces
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own content" ON content_pieces
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own content" ON content_pieces
  FOR DELETE USING (auth.uid() = user_id);

-- Templates policies (public read)
CREATE POLICY "Anyone can view templates" ON templates
  FOR SELECT USING (true);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_brand_kits_updated_at ON brand_kits;
CREATE TRIGGER update_brand_kits_updated_at
  BEFORE UPDATE ON brand_kits
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_listings_updated_at ON listings;
CREATE TRIGGER update_listings_updated_at
  BEFORE UPDATE ON listings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_content_pieces_updated_at ON content_pieces;
CREATE TRIGGER update_content_pieces_updated_at
  BEFORE UPDATE ON content_pieces
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SEED TEMPLATES (10 templates as per MVP spec)
-- =============================================================================

INSERT INTO templates (name, category, thumbnail_url, layout_config, is_premium) VALUES
-- Just Listed (3 variants)
('Minimal Modern', 'listing', '/templates/just-listed-minimal.png',
 '{"type": "just_listed", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 810}, "headline": {"x": 40, "y": 850, "fontSize": 48, "fontWeight": "bold"}, "price": {"x": 40, "y": 920, "fontSize": 36}, "details": {"x": 40, "y": 970, "fontSize": 24}, "logo": {"x": 900, "y": 980, "maxW": 150}, "banner": {"text": "JUST LISTED", "position": "top", "bg": "primary_color"}}}',
 false),

('Bold Statement', 'listing', '/templates/just-listed-bold.png',
 '{"type": "just_listed", "layout": {"photo": {"x": 0, "y": 200, "w": 1080, "h": 680}, "headline": {"x": 40, "y": 40, "fontSize": 56, "fontWeight": "black", "color": "white"}, "price": {"x": 40, "y": 920, "fontSize": 48, "fontWeight": "bold", "color": "primary"}, "details": {"x": 40, "y": 990, "fontSize": 28}, "logo": {"x": 880, "y": 40, "maxW": 160}, "banner": {"text": "JUST LISTED", "position": "overlay", "bg": "rgba(0,0,0,0.7)"}}}',
 false),

('Luxury Elegance', 'listing', '/templates/just-listed-luxury.png',
 '{"type": "just_listed", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 1080, "overlay": "gradient"}, "headline": {"x": 60, "y": 800, "fontSize": 42, "fontWeight": "light", "color": "white"}, "price": {"x": 60, "y": 870, "fontSize": 52, "fontWeight": "bold", "color": "gold"}, "details": {"x": 60, "y": 950, "fontSize": 22, "color": "white"}, "logo": {"x": 60, "y": 60, "maxW": 180}, "banner": {"text": "EXCLUSIVE", "position": "bottom", "bg": "gold"}}}',
 true),

-- Just Sold (2 variants)
('Celebration', 'listing', '/templates/just-sold-celebration.png',
 '{"type": "just_sold", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 810}, "headline": {"x": 40, "y": 850, "fontSize": 44, "fontWeight": "bold"}, "soldPrice": {"x": 40, "y": 920, "fontSize": 36, "prefix": "SOLD FOR "}, "stats": {"x": 40, "y": 980, "fontSize": 20}, "logo": {"x": 900, "y": 980, "maxW": 150}, "banner": {"text": "SOLD!", "position": "top", "bg": "success", "confetti": true}}}',
 false),

('Professional Close', 'listing', '/templates/just-sold-professional.png',
 '{"type": "just_sold", "layout": {"photo": {"x": 0, "y": 100, "w": 1080, "h": 700}, "headline": {"x": 540, "y": 40, "fontSize": 32, "fontWeight": "medium", "align": "center"}, "soldPrice": {"x": 540, "y": 840, "fontSize": 48, "fontWeight": "bold", "align": "center"}, "details": {"x": 540, "y": 920, "fontSize": 24, "align": "center"}, "logo": {"x": 465, "y": 980, "maxW": 150}, "banner": {"text": "ANOTHER SUCCESS", "position": "top", "bg": "primary_color"}}}',
 false),

-- Open House (2 variants)
('Inviting', 'listing', '/templates/open-house-inviting.png',
 '{"type": "open_house", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 750}, "headline": {"x": 40, "y": 780, "fontSize": 36, "fontWeight": "bold"}, "datetime": {"x": 40, "y": 850, "fontSize": 48, "fontWeight": "black", "color": "primary"}, "address": {"x": 40, "y": 930, "fontSize": 24}, "logo": {"x": 900, "y": 1000, "maxW": 140}, "banner": {"text": "OPEN HOUSE", "position": "top", "bg": "primary_color"}}}',
 false),

('Calendar Style', 'listing', '/templates/open-house-calendar.png',
 '{"type": "open_house", "layout": {"photo": {"x": 0, "y": 200, "w": 1080, "h": 600}, "calendarBox": {"x": 40, "y": 40, "w": 200, "h": 140, "bg": "white"}, "datetime": {"x": 140, "y": 110, "fontSize": 28, "align": "center"}, "headline": {"x": 280, "y": 80, "fontSize": 32, "fontWeight": "bold"}, "address": {"x": 40, "y": 840, "fontSize": 28}, "logo": {"x": 900, "y": 1000, "maxW": 140}, "banner": {"text": "YOU ARE INVITED", "position": "bottom", "bg": "secondary_color"}}}',
 true),

-- Price Reduction (1 variant)
('Price Drop Alert', 'listing', '/templates/price-drop-alert.png',
 '{"type": "price_drop", "layout": {"photo": {"x": 0, "y": 150, "w": 1080, "h": 650}, "oldPrice": {"x": 40, "y": 50, "fontSize": 32, "strikethrough": true, "color": "gray"}, "newPrice": {"x": 40, "y": 100, "fontSize": 56, "fontWeight": "black", "color": "error"}, "savings": {"x": 300, "y": 70, "fontSize": 28, "badge": true, "bg": "error"}, "headline": {"x": 40, "y": 840, "fontSize": 36, "fontWeight": "bold"}, "details": {"x": 40, "y": 900, "fontSize": 24}, "logo": {"x": 900, "y": 1000, "maxW": 140}, "banner": {"text": "PRICE REDUCED!", "position": "diagonal", "bg": "error"}}}',
 false),

-- Coming Soon (2 variants)
('Teaser', 'listing', '/templates/coming-soon-teaser.png',
 '{"type": "coming_soon", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 1080, "blur": 5, "overlay": "dark"}, "headline": {"x": 540, "y": 400, "fontSize": 64, "fontWeight": "black", "color": "white", "align": "center"}, "subtext": {"x": 540, "y": 500, "fontSize": 28, "color": "white", "align": "center"}, "details": {"x": 540, "y": 600, "fontSize": 32, "color": "white", "align": "center"}, "logo": {"x": 465, "y": 900, "maxW": 150}, "banner": {"text": "COMING SOON", "position": "center", "bg": "transparent"}}}',
 false),

('Sneak Peek', 'listing', '/templates/coming-soon-sneak.png',
 '{"type": "coming_soon", "layout": {"photo": {"x": 0, "y": 0, "w": 1080, "h": 800, "mask": "peek"}, "headline": {"x": 40, "y": 840, "fontSize": 42, "fontWeight": "bold"}, "neighborhood": {"x": 40, "y": 910, "fontSize": 28, "color": "secondary"}, "teaser": {"x": 40, "y": 960, "fontSize": 22}, "logo": {"x": 900, "y": 1000, "maxW": 140}, "banner": {"text": "SNEAK PEEK", "position": "top", "bg": "primary_color"}}}',
 true);

-- =============================================================================
-- STORAGE BUCKETS (Create via Supabase Dashboard)
-- =============================================================================
--
-- Create these buckets in Supabase Dashboard > Storage:
--
-- 1. listing-photos
--    - Public: false
--    - File size limit: 10MB
--    - Allowed types: image/*
--
-- 2. brand-assets
--    - Public: true (logos can be public)
--    - File size limit: 5MB
--    - Allowed types: image/*
--
-- 3. generated-content
--    - Public: false
--    - File size limit: 50MB
--    - Allowed types: image/*
-- =============================================================================
