-- Seed Templates Data
-- 10 initial templates as per MVP spec

INSERT INTO templates (id, name, category, thumbnail_url, layout_config, is_premium) VALUES
-- Just Listed Templates (3 variants)
(
  uuid_generate_v4(),
  'Minimal Modern',
  'listing',
  '/templates/just-listed-minimal.png',
  '{
    "id": "just-listed-minimal",
    "type": "just_listed",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 810 },
      "headline": { "x": 40, "y": 850, "fontSize": 48, "fontWeight": "bold", "color": "primary" },
      "price": { "x": 40, "y": 920, "fontSize": 36, "fontWeight": "semibold" },
      "details": { "x": 40, "y": 970, "fontSize": 24 },
      "logo": { "x": 900, "y": 980, "maxW": 150 },
      "banner": { "text": "JUST LISTED", "position": "top", "bg": "primary_color" }
    }
  }',
  false
),
(
  uuid_generate_v4(),
  'Bold Statement',
  'listing',
  '/templates/just-listed-bold.png',
  '{
    "id": "just-listed-bold",
    "type": "just_listed",
    "layout": {
      "photo": { "x": 0, "y": 200, "w": 1080, "h": 680 },
      "headline": { "x": 40, "y": 40, "fontSize": 56, "fontWeight": "black", "color": "white" },
      "price": { "x": 40, "y": 920, "fontSize": 48, "fontWeight": "bold", "color": "primary" },
      "details": { "x": 40, "y": 990, "fontSize": 28 },
      "logo": { "x": 880, "y": 40, "maxW": 160 },
      "banner": { "text": "JUST LISTED", "position": "overlay", "bg": "rgba(0,0,0,0.7)" }
    }
  }',
  false
),
(
  uuid_generate_v4(),
  'Luxury Elegance',
  'listing',
  '/templates/just-listed-luxury.png',
  '{
    "id": "just-listed-luxury",
    "type": "just_listed",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 1080, "overlay": "gradient" },
      "headline": { "x": 60, "y": 800, "fontSize": 42, "fontWeight": "light", "color": "white", "letterSpacing": 2 },
      "price": { "x": 60, "y": 870, "fontSize": 52, "fontWeight": "bold", "color": "gold" },
      "details": { "x": 60, "y": 950, "fontSize": 22, "color": "white" },
      "logo": { "x": 60, "y": 60, "maxW": 180 },
      "banner": { "text": "EXCLUSIVE LISTING", "position": "bottom", "bg": "gold" }
    }
  }',
  true
),

-- Just Sold Templates (2 variants)
(
  uuid_generate_v4(),
  'Celebration',
  'listing',
  '/templates/just-sold-celebration.png',
  '{
    "id": "just-sold-celebration",
    "type": "just_sold",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 810 },
      "headline": { "x": 40, "y": 850, "fontSize": 44, "fontWeight": "bold" },
      "soldPrice": { "x": 40, "y": 920, "fontSize": 36, "prefix": "SOLD FOR " },
      "stats": { "x": 40, "y": 980, "fontSize": 20, "showDaysOnMarket": true },
      "logo": { "x": 900, "y": 980, "maxW": 150 },
      "banner": { "text": "SOLD!", "position": "top", "bg": "success_color", "confetti": true }
    }
  }',
  false
),
(
  uuid_generate_v4(),
  'Professional Close',
  'listing',
  '/templates/just-sold-professional.png',
  '{
    "id": "just-sold-professional",
    "type": "just_sold",
    "layout": {
      "photo": { "x": 0, "y": 100, "w": 1080, "h": 700 },
      "headline": { "x": 540, "y": 40, "fontSize": 32, "fontWeight": "medium", "align": "center" },
      "soldPrice": { "x": 540, "y": 840, "fontSize": 48, "fontWeight": "bold", "align": "center" },
      "details": { "x": 540, "y": 920, "fontSize": 24, "align": "center" },
      "logo": { "x": 465, "y": 980, "maxW": 150 },
      "banner": { "text": "ANOTHER SUCCESS STORY", "position": "top", "bg": "primary_color" }
    }
  }',
  false
),

-- Open House Templates (2 variants)
(
  uuid_generate_v4(),
  'Inviting',
  'listing',
  '/templates/open-house-inviting.png',
  '{
    "id": "open-house-inviting",
    "type": "open_house",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 750 },
      "headline": { "x": 40, "y": 780, "fontSize": 36, "fontWeight": "bold" },
      "datetime": { "x": 40, "y": 850, "fontSize": 48, "fontWeight": "black", "color": "primary" },
      "address": { "x": 40, "y": 930, "fontSize": 24 },
      "logo": { "x": 900, "y": 1000, "maxW": 140 },
      "banner": { "text": "OPEN HOUSE", "position": "top", "bg": "primary_color" }
    }
  }',
  false
),
(
  uuid_generate_v4(),
  'Calendar Style',
  'listing',
  '/templates/open-house-calendar.png',
  '{
    "id": "open-house-calendar",
    "type": "open_house",
    "layout": {
      "photo": { "x": 0, "y": 200, "w": 1080, "h": 600 },
      "calendarBox": { "x": 40, "y": 40, "w": 200, "h": 140, "bg": "white", "shadow": true },
      "datetime": { "x": 140, "y": 110, "fontSize": 28, "align": "center" },
      "headline": { "x": 280, "y": 80, "fontSize": 32, "fontWeight": "bold" },
      "address": { "x": 40, "y": 840, "fontSize": 28 },
      "details": { "x": 40, "y": 900, "fontSize": 22 },
      "logo": { "x": 900, "y": 1000, "maxW": 140 },
      "banner": { "text": "YOU''RE INVITED", "position": "bottom", "bg": "secondary_color" }
    }
  }',
  true
),

-- Price Reduction Template (1 variant)
(
  uuid_generate_v4(),
  'Price Drop Alert',
  'listing',
  '/templates/price-drop-alert.png',
  '{
    "id": "price-drop-alert",
    "type": "price_drop",
    "layout": {
      "photo": { "x": 0, "y": 150, "w": 1080, "h": 650 },
      "oldPrice": { "x": 40, "y": 50, "fontSize": 32, "strikethrough": true, "color": "gray" },
      "newPrice": { "x": 40, "y": 100, "fontSize": 56, "fontWeight": "black", "color": "error" },
      "savings": { "x": 300, "y": 70, "fontSize": 28, "badge": true, "bg": "error" },
      "headline": { "x": 40, "y": 840, "fontSize": 36, "fontWeight": "bold" },
      "details": { "x": 40, "y": 900, "fontSize": 24 },
      "logo": { "x": 900, "y": 1000, "maxW": 140 },
      "banner": { "text": "PRICE REDUCED!", "position": "diagonal", "bg": "error_color" }
    }
  }',
  false
),

-- Coming Soon Templates (2 variants)
(
  uuid_generate_v4(),
  'Teaser',
  'listing',
  '/templates/coming-soon-teaser.png',
  '{
    "id": "coming-soon-teaser",
    "type": "coming_soon",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 1080, "blur": 5, "overlay": "dark" },
      "headline": { "x": 540, "y": 400, "fontSize": 64, "fontWeight": "black", "color": "white", "align": "center" },
      "subtext": { "x": 540, "y": 500, "fontSize": 28, "color": "white", "align": "center" },
      "details": { "x": 540, "y": 600, "fontSize": 32, "color": "white", "align": "center" },
      "logo": { "x": 465, "y": 900, "maxW": 150 },
      "banner": { "text": "COMING SOON", "position": "center", "bg": "transparent" }
    }
  }',
  false
),
(
  uuid_generate_v4(),
  'Sneak Peek',
  'listing',
  '/templates/coming-soon-sneak.png',
  '{
    "id": "coming-soon-sneak",
    "type": "coming_soon",
    "layout": {
      "photo": { "x": 0, "y": 0, "w": 1080, "h": 800, "mask": "peek" },
      "headline": { "x": 40, "y": 840, "fontSize": 42, "fontWeight": "bold" },
      "neighborhood": { "x": 40, "y": 910, "fontSize": 28, "color": "secondary" },
      "teaser": { "x": 40, "y": 960, "fontSize": 22 },
      "logo": { "x": 900, "y": 1000, "maxW": 140 },
      "banner": { "text": "SNEAK PEEK", "position": "top", "bg": "primary_color" }
    }
  }',
  true
);
