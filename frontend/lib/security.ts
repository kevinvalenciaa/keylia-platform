/**
 * Security Utilities
 *
 * CSRF protection, security headers, and request validation.
 */

import { NextRequest, NextResponse } from "next/server";

/**
 * Allowed origins for CSRF protection.
 * Add your production domains here.
 */
const ALLOWED_ORIGINS = [
  process.env.NEXT_PUBLIC_APP_URL,
  "http://localhost:3000",
  "http://localhost:3001",
].filter(Boolean) as string[];

/**
 * Paths that should skip CSRF validation (public endpoints).
 */
const CSRF_EXEMPT_PATHS = [
  "/api/webhooks/stripe", // Stripe webhooks have their own signature verification
  "/api/health",
  "/health",
];

/**
 * HTTP methods that modify state and require CSRF protection.
 */
const CSRF_PROTECTED_METHODS = ["POST", "PUT", "PATCH", "DELETE"];

/**
 * Security headers to add to all responses.
 * These provide defense-in-depth against common web attacks.
 */
export const SECURITY_HEADERS: Record<string, string> = {
  // Prevent MIME type sniffing
  "X-Content-Type-Options": "nosniff",

  // Prevent clickjacking
  "X-Frame-Options": "DENY",

  // XSS protection (legacy, but still useful for older browsers)
  "X-XSS-Protection": "1; mode=block",

  // Referrer policy - only send origin for cross-origin requests
  "Referrer-Policy": "strict-origin-when-cross-origin",

  // Permissions policy - disable unnecessary browser features
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};

/**
 * Content Security Policy for production.
 * Adjust based on your specific needs.
 */
export function getCSPHeader(nonce?: string): string {
  const directives = [
    "default-src 'self'",
    `script-src 'self'${nonce ? ` 'nonce-${nonce}'` : ""} 'unsafe-inline' 'unsafe-eval'`, // Next.js requires unsafe-eval in dev
    "style-src 'self' 'unsafe-inline'", // Many UI libraries need inline styles
    "img-src 'self' data: https: blob:",
    "font-src 'self' data:",
    "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://api.anthropic.com https://api.stripe.com https://api.elevenlabs.io",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ];

  return directives.join("; ");
}

/**
 * Validate request origin for CSRF protection.
 *
 * Checks that the Origin or Referer header matches an allowed origin.
 * This prevents cross-site request forgery attacks.
 *
 * @param request - The incoming request
 * @returns true if the request passes CSRF validation
 */
export function validateCSRF(request: NextRequest): {
  valid: boolean;
  reason?: string;
} {
  const method = request.method;
  const pathname = request.nextUrl.pathname;

  // Skip validation for safe methods (GET, HEAD, OPTIONS)
  if (!CSRF_PROTECTED_METHODS.includes(method)) {
    return { valid: true };
  }

  // Skip validation for exempt paths
  if (CSRF_EXEMPT_PATHS.some((path) => pathname.startsWith(path))) {
    return { valid: true };
  }

  // Get origin from headers
  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");

  // Extract origin from referer if origin is not present
  let requestOrigin = origin;
  if (!requestOrigin && referer) {
    try {
      requestOrigin = new URL(referer).origin;
    } catch {
      // Invalid referer URL
    }
  }

  // If no origin information, reject (except for same-origin requests)
  if (!requestOrigin) {
    // Allow requests without origin if they're from server-side (no origin header)
    // This happens with tRPC server components
    const secFetchSite = request.headers.get("sec-fetch-site");
    if (secFetchSite === "same-origin" || secFetchSite === "none") {
      return { valid: true };
    }

    // For API routes, require origin header on mutations
    if (pathname.startsWith("/api/")) {
      return { valid: false, reason: "Missing origin header" };
    }

    return { valid: true };
  }

  // Check if origin is allowed
  const isAllowed = ALLOWED_ORIGINS.some((allowed) => {
    try {
      return new URL(allowed).origin === requestOrigin;
    } catch {
      return false;
    }
  });

  if (!isAllowed) {
    return { valid: false, reason: `Origin not allowed: ${requestOrigin}` };
  }

  return { valid: true };
}

/**
 * Apply security headers to a response.
 *
 * @param response - The response to modify
 * @param options - Options for header generation
 * @returns The response with security headers added
 */
export function applySecurityHeaders(
  response: NextResponse,
  options: { includeCSP?: boolean; nonce?: string } = {}
): NextResponse {
  // Add standard security headers
  for (const [header, value] of Object.entries(SECURITY_HEADERS)) {
    response.headers.set(header, value);
  }

  // Add CSP header if requested
  if (options.includeCSP) {
    response.headers.set("Content-Security-Policy", getCSPHeader(options.nonce));
  }

  // Add Strict-Transport-Security for production
  if (process.env.NODE_ENV === "production") {
    response.headers.set(
      "Strict-Transport-Security",
      "max-age=31536000; includeSubDomains"
    );
  }

  return response;
}

/**
 * Create a CSRF error response.
 */
export function createCSRFErrorResponse(reason: string): NextResponse {
  return new NextResponse(
    JSON.stringify({
      error: "CSRF validation failed",
      message: reason,
    }),
    {
      status: 403,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

/**
 * Generate a cryptographically secure nonce for CSP.
 */
export function generateNonce(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Buffer.from(array).toString("base64");
}
