/**
 * Security Tests for XSS Prevention and URL Validation
 *
 * These tests verify that the security utility functions properly
 * prevent XSS attacks via malicious URLs and other vectors.
 */

import { describe, it, expect } from "vitest";
import { isValidImageUrl, sanitizeImageUrl } from "@/lib/utils";

describe("isValidImageUrl", () => {
  describe("valid URLs", () => {
    it("accepts https URLs", () => {
      expect(isValidImageUrl("https://example.com/image.jpg")).toBe(true);
      expect(isValidImageUrl("https://cdn.example.com/path/to/image.png")).toBe(
        true
      );
    });

    it("accepts http URLs", () => {
      expect(isValidImageUrl("http://example.com/image.jpg")).toBe(true);
    });

    it("accepts relative URLs starting with /", () => {
      expect(isValidImageUrl("/images/photo.jpg")).toBe(true);
      expect(isValidImageUrl("/api/images/123")).toBe(true);
    });

    it("accepts safe data URLs for images", () => {
      expect(isValidImageUrl("data:image/jpeg;base64,/9j/4AAQ")).toBe(true);
      expect(isValidImageUrl("data:image/png;base64,iVBORw")).toBe(true);
      expect(isValidImageUrl("data:image/gif;base64,R0lGOD")).toBe(true);
      expect(isValidImageUrl("data:image/webp;base64,UklGR")).toBe(true);
      expect(isValidImageUrl("data:image/svg+xml;base64,PHN2Z")).toBe(true);
    });

    it("handles URLs with query parameters", () => {
      expect(isValidImageUrl("https://example.com/image.jpg?size=large")).toBe(
        true
      );
    });

    it("handles URLs with fragments", () => {
      expect(isValidImageUrl("https://example.com/image.jpg#section")).toBe(
        true
      );
    });
  });

  describe("XSS attack prevention", () => {
    it("rejects javascript: URLs", () => {
      expect(isValidImageUrl("javascript:alert('xss')")).toBe(false);
      expect(isValidImageUrl("javascript:void(0)")).toBe(false);
      expect(isValidImageUrl("JAVASCRIPT:alert(1)")).toBe(false);
      expect(isValidImageUrl("  javascript:alert(1)  ")).toBe(false);
    });

    it("rejects vbscript: URLs", () => {
      expect(isValidImageUrl("vbscript:msgbox('xss')")).toBe(false);
    });

    it("rejects data URLs with non-image MIME types", () => {
      expect(isValidImageUrl("data:text/html;base64,PHNjcmlwdD4=")).toBe(false);
      expect(
        isValidImageUrl("data:application/javascript;base64,YWxlcnQ=")
      ).toBe(false);
      expect(isValidImageUrl("data:text/plain;base64,dGVzdA==")).toBe(false);
    });

    it("rejects protocol-relative URLs", () => {
      // Protocol-relative URLs could be used to bypass protocol checks
      expect(isValidImageUrl("//evil.com/image.jpg")).toBe(false);
    });

    it("rejects URLs with credentials", () => {
      // URLs with embedded credentials are a security risk
      expect(isValidImageUrl("https://user:pass@example.com/image.jpg")).toBe(
        false
      );
    });
  });

  describe("edge cases", () => {
    it("rejects null and undefined", () => {
      expect(isValidImageUrl(null)).toBe(false);
      expect(isValidImageUrl(undefined)).toBe(false);
    });

    it("rejects empty strings", () => {
      expect(isValidImageUrl("")).toBe(false);
      expect(isValidImageUrl("   ")).toBe(false);
    });

    it("rejects non-string values", () => {
      // @ts-expect-error - testing runtime behavior with wrong types
      expect(isValidImageUrl(123)).toBe(false);
      // @ts-expect-error - testing runtime behavior with wrong types
      expect(isValidImageUrl({})).toBe(false);
      // @ts-expect-error - testing runtime behavior with wrong types
      expect(isValidImageUrl([])).toBe(false);
    });

    it("handles URLs with unicode characters", () => {
      expect(isValidImageUrl("https://example.com/图片.jpg")).toBe(true);
    });

    it("handles very long URLs", () => {
      const longPath = "a".repeat(2000);
      expect(isValidImageUrl(`https://example.com/${longPath}`)).toBe(true);
    });
  });
});

describe("sanitizeImageUrl", () => {
  it("returns valid URLs unchanged", () => {
    expect(sanitizeImageUrl("https://example.com/image.jpg")).toBe(
      "https://example.com/image.jpg"
    );
  });

  it("trims whitespace from valid URLs", () => {
    expect(sanitizeImageUrl("  https://example.com/image.jpg  ")).toBe(
      "https://example.com/image.jpg"
    );
  });

  it("returns empty string for invalid URLs", () => {
    expect(sanitizeImageUrl("javascript:alert(1)")).toBe("");
    expect(sanitizeImageUrl(null)).toBe("");
    expect(sanitizeImageUrl(undefined)).toBe("");
    expect(sanitizeImageUrl("")).toBe("");
  });

  it("returns empty string for XSS attempts", () => {
    expect(sanitizeImageUrl("javascript:alert('xss')")).toBe("");
    expect(sanitizeImageUrl("data:text/html;base64,PHNjcmlwdD4=")).toBe("");
  });
});
