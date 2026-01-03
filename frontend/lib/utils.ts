import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Validates that a URL is safe for use in image src attributes.
 * Prevents XSS attacks via javascript: URLs and other malicious protocols.
 *
 * @param url - The URL to validate
 * @returns true if the URL is safe for image rendering
 */
export function isValidImageUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== "string") {
    return false;
  }

  // Trim and check for empty string
  const trimmedUrl = url.trim();
  if (trimmedUrl.length === 0) {
    return false;
  }

  // Block javascript: and data: URLs (except safe image data URLs)
  const lowerUrl = trimmedUrl.toLowerCase();
  if (lowerUrl.startsWith("javascript:")) {
    return false;
  }

  // Allow data URLs only for images with safe MIME types
  if (lowerUrl.startsWith("data:")) {
    const safeImageMimes = [
      "data:image/jpeg",
      "data:image/jpg",
      "data:image/png",
      "data:image/gif",
      "data:image/webp",
      "data:image/svg+xml",
    ];
    return safeImageMimes.some((mime) => lowerUrl.startsWith(mime));
  }

  // Validate URL structure
  try {
    const parsed = new URL(trimmedUrl);

    // Only allow http and https protocols
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return false;
    }

    // Block URLs with credentials (potential security risk)
    if (parsed.username || parsed.password) {
      return false;
    }

    return true;
  } catch {
    // If URL parsing fails, check if it's a relative URL (starts with /)
    return trimmedUrl.startsWith("/") && !trimmedUrl.startsWith("//");
  }
}

/**
 * Sanitizes a URL for safe use in image src attributes.
 * Returns empty string if URL is not safe.
 *
 * @param url - The URL to sanitize
 * @returns The sanitized URL or empty string
 */
export function sanitizeImageUrl(url: string | null | undefined): string {
  if (isValidImageUrl(url)) {
    return url!.trim();
  }
  return "";
}

