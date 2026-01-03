import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";
import {
  validateCSRF,
  applySecurityHeaders,
  createCSRFErrorResponse,
} from "@/lib/security";

/**
 * Next.js Middleware
 *
 * This middleware runs on every request and handles:
 * 1. CSRF protection for state-changing requests
 * 2. Security headers (XSS, clickjacking, etc.)
 * 3. Supabase session management
 */
export async function middleware(request: NextRequest) {
  // 1. CSRF Protection
  // Validate origin/referer for state-changing requests
  const csrfValidation = validateCSRF(request);
  if (!csrfValidation.valid) {
    console.warn(`CSRF validation failed: ${csrfValidation.reason}`, {
      path: request.nextUrl.pathname,
      method: request.method,
      origin: request.headers.get("origin"),
    });
    return createCSRFErrorResponse(csrfValidation.reason || "Invalid request");
  }

  // 2. Update Supabase session
  // This handles auth token refresh and cookie management
  const response = await updateSession(request);

  // 3. Apply security headers
  // Add headers to protect against common web attacks
  applySecurityHeaders(response, {
    // Enable CSP in production only (can break dev hot reload)
    includeCSP: process.env.NODE_ENV === "production",
  });

  return response;
}

export const config = {
  matcher: [
    // Match all paths except:
    // - Static files (_next/static, _next/image)
    // - Favicon and common static assets
    // - Public images
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
