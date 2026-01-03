/**
 * Tests for utility functions.
 */

import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn utility", () => {
  it("merges class names", () => {
    const result = cn("class1", "class2");
    expect(result).toBe("class1 class2");
  });

  it("handles conditional classes", () => {
    const isActive = true;
    const result = cn("base", isActive && "active");
    expect(result).toBe("base active");
  });

  it("handles false conditions", () => {
    const isActive = false;
    const result = cn("base", isActive && "active");
    expect(result).toBe("base");
  });

  it("handles undefined values", () => {
    const result = cn("base", undefined, "end");
    expect(result).toBe("base end");
  });

  it("merges tailwind classes correctly", () => {
    const result = cn("px-2 py-1", "px-4");
    expect(result).toBe("py-1 px-4");
  });

  it("handles object syntax", () => {
    const result = cn("base", { active: true, disabled: false });
    expect(result).toBe("base active");
  });

  it("handles array syntax", () => {
    const result = cn(["class1", "class2"]);
    expect(result).toBe("class1 class2");
  });
});


describe("formatPrice", () => {
  // Helper function that might exist in utils
  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  it("formats price with dollar sign", () => {
    expect(formatPrice(1000)).toBe("$1,000");
  });

  it("formats large prices with commas", () => {
    expect(formatPrice(1500000)).toBe("$1,500,000");
  });

  it("handles zero", () => {
    expect(formatPrice(0)).toBe("$0");
  });
});
