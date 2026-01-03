/**
 * Input Sanitization Utilities
 *
 * Prevents prompt injection and XSS attacks by sanitizing user input
 * before including it in AI prompts or rendering.
 */

/**
 * Patterns that could be used for prompt injection attacks.
 * These are common patterns attackers use to manipulate AI systems.
 */
const PROMPT_INJECTION_PATTERNS = [
  // Direct instruction overrides (with optional articles "the", "all")
  /ignore\s+(all\s+|the\s+)?(previous|prior|above)\s+(instructions?|prompts?|context)/gi,
  /(please\s+)?ignore\s+(all\s+|the\s+)?(previous|prior|above)/gi,
  /disregard\s+(all\s+|the\s+)?(previous|prior|above)/gi,
  /forget\s+(everything|all|what)\s+(you|i)\s+(said|told|wrote)/gi,

  // System prompt extraction attempts
  /what\s+(are|is)\s+(your|the)\s+(instructions?|prompts?|system)/gi,
  /show\s+(me\s+)?(your|the)\s+(system|original)\s+prompt/gi,
  /repeat\s+(your|the)\s+(system|initial)\s+(prompt|instructions?)/gi,
  /print\s+(your|the)\s+(system|initial)\s+(prompt|instructions?)/gi,

  // Role manipulation
  /you\s+are\s+now\s+(a|an)\s+/gi,
  /pretend\s+(to\s+be|you\s+are)\s+/gi,
  /act\s+as\s+(if\s+you\s+are|a|an)\s+/gi,
  /roleplay\s+as\s+/gi,

  // Delimiter injection
  /={3,}/g,
  /#{3,}/g,
  /-{3,}/g,

  // Code/command injection
  /<\/?script/gi,
  /javascript:/gi,
  /eval\s*\(/gi,
  /exec\s*\(/gi,

  // Output manipulation
  /output\s+only/gi,
  /respond\s+only\s+with/gi,
  /say\s+only/gi,
];

/**
 * Sanitize text for safe inclusion in AI prompts.
 * Removes or neutralizes potential prompt injection patterns.
 *
 * @param text - The text to sanitize
 * @param maxLength - Maximum length (default: 10000)
 * @returns Sanitized text
 */
export function sanitizeForPrompt(text: string | null | undefined, maxLength = 10000): string {
  if (!text) return "";

  let sanitized = text;

  // Truncate to max length
  if (sanitized.length > maxLength) {
    sanitized = sanitized.slice(0, maxLength);
  }

  // Remove or neutralize prompt injection patterns
  for (const pattern of PROMPT_INJECTION_PATTERNS) {
    sanitized = sanitized.replace(pattern, "[filtered]");
  }

  // Remove control characters except newlines and tabs
  sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");

  // Normalize whitespace (collapse multiple spaces/newlines)
  sanitized = sanitized.replace(/\n{3,}/g, "\n\n");
  sanitized = sanitized.replace(/[ \t]{3,}/g, "  ");

  // Escape special markdown/formatting characters that could affect prompt structure
  sanitized = sanitized.replace(/```/g, "'''"); // Triple backticks
  sanitized = sanitized.replace(/"""/g, "'''"); // Triple quotes

  return sanitized.trim();
}

/**
 * Sanitize an array of strings for prompt inclusion.
 *
 * @param items - Array of strings to sanitize
 * @param maxItems - Maximum number of items (default: 50)
 * @param maxItemLength - Maximum length per item (default: 200)
 * @returns Sanitized array
 */
export function sanitizeArrayForPrompt(
  items: string[] | null | undefined,
  maxItems = 50,
  maxItemLength = 200
): string[] {
  if (!items || !Array.isArray(items)) return [];

  return items
    .slice(0, maxItems)
    .map((item) => sanitizeForPrompt(item, maxItemLength))
    .filter((item) => item.length > 0);
}

/**
 * Escape HTML entities to prevent XSS.
 *
 * @param text - The text to escape
 * @returns HTML-safe text
 */
export function escapeHtml(text: string | null | undefined): string {
  if (!text) return "";

  const htmlEntities: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
    "/": "&#x2F;",
    "`": "&#x60;",
    "=": "&#x3D;",
  };

  return text.replace(/[&<>"'`=/]/g, (char) => htmlEntities[char] || char);
}

/**
 * Sanitize a URL to prevent javascript: and data: attacks.
 *
 * @param url - The URL to sanitize
 * @returns Sanitized URL or empty string if invalid
 */
export function sanitizeUrl(url: string | null | undefined): string {
  if (!url) return "";

  const trimmed = url.trim().toLowerCase();

  // Block dangerous protocols
  if (
    trimmed.startsWith("javascript:") ||
    trimmed.startsWith("data:") ||
    trimmed.startsWith("vbscript:")
  ) {
    return "";
  }

  // Only allow http, https, and relative URLs
  if (
    trimmed.startsWith("http://") ||
    trimmed.startsWith("https://") ||
    trimmed.startsWith("/") ||
    !trimmed.includes(":")
  ) {
    return url.trim();
  }

  return "";
}

/**
 * Create a safe property description from listing data.
 * This is specifically designed for real estate AI prompts.
 *
 * @param listing - The listing data object
 * @returns Sanitized description string
 */
export function createSafePropertyDescription(listing: {
  address_line1?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  listing_price?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  square_feet?: number | null;
  property_type?: string | null;
  features?: string[] | null;
  positioning_notes?: string | null;
}): string {
  const parts: string[] = [];

  // Address (sanitized)
  const address = sanitizeForPrompt(listing.address_line1, 200);
  const city = sanitizeForPrompt(listing.city, 100);
  const state = sanitizeForPrompt(listing.state, 50);
  const zip = sanitizeForPrompt(listing.zip_code, 20);

  if (address) {
    parts.push(`Address: ${address}, ${city}, ${state} ${zip}`.trim());
  }

  // Price (validated as number)
  const price = typeof listing.listing_price === "number" && listing.listing_price >= 0
    ? listing.listing_price
    : 0;
  parts.push(`Price: $${price.toLocaleString()}`);

  // Details (validated as numbers)
  const bedrooms = typeof listing.bedrooms === "number" ? Math.max(0, Math.min(listing.bedrooms, 100)) : 0;
  const bathrooms = typeof listing.bathrooms === "number" ? Math.max(0, Math.min(listing.bathrooms, 100)) : 0;
  const sqft = typeof listing.square_feet === "number" ? Math.max(0, Math.min(listing.square_feet, 100000000)) : 0;
  parts.push(`Details: ${bedrooms}bd/${bathrooms}ba, ${sqft.toLocaleString()} sqft`);

  // Property type (sanitized, limited values)
  const propertyType = sanitizeForPrompt(listing.property_type, 50);
  if (propertyType) {
    parts.push(`Type: ${propertyType.replace("_", " ")}`);
  }

  // Features (sanitized array)
  const features = sanitizeArrayForPrompt(listing.features, 20, 100);
  if (features.length > 0) {
    parts.push(`Key Features: ${features.join(", ")}`);
  }

  // Description (sanitized, longer limit)
  const description = sanitizeForPrompt(listing.positioning_notes, 2000);
  if (description) {
    parts.push(`Description: ${description}`);
  }

  return parts.join("\n");
}
