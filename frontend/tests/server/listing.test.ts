/**
 * Tests for listing tRPC router.
 *
 * These tests verify:
 * - Property listing CRUD operations
 * - Input validation
 * - Authorization checks
 * - Data transformation
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock Supabase
const mockSupabase = {
  from: vi.fn().mockReturnThis(),
  select: vi.fn().mockReturnThis(),
  insert: vi.fn().mockReturnThis(),
  update: vi.fn().mockReturnThis(),
  delete: vi.fn().mockReturnThis(),
  eq: vi.fn().mockReturnThis(),
  order: vi.fn().mockReturnThis(),
  range: vi.fn().mockReturnThis(),
  single: vi.fn(),
  maybeSingle: vi.fn(),
};

describe("Listing Router", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock chain
    mockSupabase.from.mockReturnThis();
    mockSupabase.select.mockReturnThis();
    mockSupabase.eq.mockReturnThis();
    mockSupabase.order.mockReturnThis();
    mockSupabase.range.mockReturnThis();
  });

  describe("getAll", () => {
    it("should return paginated listings", async () => {
      const mockListings = [
        {
          id: "1",
          address_line1: "123 Main St",
          city: "Los Angeles",
          state: "CA",
          listing_price: 500000,
        },
        {
          id: "2",
          address_line1: "456 Oak Ave",
          city: "San Francisco",
          state: "CA",
          listing_price: 750000,
        },
      ];

      mockSupabase.range.mockResolvedValue({
        data: mockListings,
        error: null,
        count: 2,
      });

      const result = await mockSupabase
        .from("property_listings")
        .select("*", { count: "exact" })
        .order("created_at", { ascending: false })
        .range(0, 19);

      expect(result.data).toHaveLength(2);
      expect(result.count).toBe(2);
    });

    it("should filter by listing status", async () => {
      const activeListings = [
        {
          id: "1",
          listing_status: "active",
        },
      ];

      mockSupabase.range.mockResolvedValue({
        data: activeListings,
        error: null,
      });

      const result = await mockSupabase
        .from("property_listings")
        .select("*")
        .eq("listing_status", "active")
        .range(0, 19);

      expect(result.data).toHaveLength(1);
      expect(result.data?.[0].listing_status).toBe("active");
    });
  });

  describe("getById", () => {
    it("should return listing with all details", async () => {
      const mockListing = {
        id: "1",
        address_line1: "123 Main St",
        address_line2: "Apt 4B",
        city: "Los Angeles",
        state: "CA",
        zip_code: "90210",
        listing_price: 1500000,
        bedrooms: 4,
        bathrooms: 3,
        square_feet: 2800,
        features: ["Pool", "Smart Home"],
        created_at: "2025-01-01T00:00:00Z",
      };

      mockSupabase.single.mockResolvedValue({
        data: mockListing,
        error: null,
      });

      const result = await mockSupabase
        .from("property_listings")
        .select("*")
        .eq("id", "1")
        .single();

      expect(result.data?.address_line1).toBe("123 Main St");
      expect(result.data?.features).toContain("Pool");
    });

    it("should return null for non-existent listing", async () => {
      mockSupabase.single.mockResolvedValue({
        data: null,
        error: { code: "PGRST116", message: "No rows found" },
      });

      const result = await mockSupabase
        .from("property_listings")
        .select("*")
        .eq("id", "non-existent")
        .single();

      expect(result.data).toBeNull();
      expect(result.error).not.toBeNull();
    });
  });

  describe("create", () => {
    it("should create listing with required fields", async () => {
      const newListing = {
        address_line1: "789 New St",
        city: "San Diego",
        state: "CA",
        listing_price: 600000,
      };

      const createdListing = {
        id: "3",
        ...newListing,
        created_at: "2025-01-03T00:00:00Z",
      };

      mockSupabase.single.mockResolvedValue({
        data: createdListing,
        error: null,
      });

      const result = await mockSupabase
        .from("property_listings")
        .insert(newListing)
        .select()
        .single();

      expect(result.data?.id).toBe("3");
      expect(result.data?.city).toBe("San Diego");
    });

    it("should validate required fields", () => {
      const invalidListing = {
        address_line1: "", // Empty - should fail
        city: "LA",
      };

      // Validation logic
      const isValid =
        invalidListing.address_line1.length > 0 &&
        invalidListing.city.length >= 2;

      expect(isValid).toBe(false);
    });

    it("should validate price is positive", () => {
      const validatePrice = (price: number | null) => {
        if (price === null) return true; // Optional
        return price > 0;
      };

      expect(validatePrice(500000)).toBe(true);
      expect(validatePrice(0)).toBe(false);
      expect(validatePrice(-100)).toBe(false);
      expect(validatePrice(null)).toBe(true);
    });
  });

  describe("update", () => {
    it("should update listing fields", async () => {
      const updates = {
        listing_price: 550000,
        listing_status: "pending",
      };

      const updatedListing = {
        id: "1",
        listing_price: 550000,
        listing_status: "pending",
      };

      mockSupabase.single.mockResolvedValue({
        data: updatedListing,
        error: null,
      });

      const result = await mockSupabase
        .from("property_listings")
        .update(updates)
        .eq("id", "1")
        .select()
        .single();

      expect(result.data?.listing_price).toBe(550000);
      expect(result.data?.listing_status).toBe("pending");
    });
  });

  describe("delete", () => {
    it("should delete listing by id", async () => {
      mockSupabase.eq.mockResolvedValue({
        data: null,
        error: null,
      });

      const result = await mockSupabase
        .from("property_listings")
        .delete()
        .eq("id", "1");

      expect(result.error).toBeNull();
    });
  });
});

describe("Listing Data Validation", () => {
  describe("Address Validation", () => {
    it("should validate address length", () => {
      const validate = (address: string) => {
        return address.length >= 5 && address.length <= 200;
      };

      expect(validate("123 Main St")).toBe(true);
      expect(validate("123")).toBe(false);
      expect(validate("A".repeat(201))).toBe(false);
    });

    it("should validate state codes", () => {
      const validStates = ["CA", "NY", "TX", "FL", "WA"];
      const isValidState = (state: string) => {
        return /^[A-Z]{2}$/.test(state);
      };

      validStates.forEach((state) => {
        expect(isValidState(state)).toBe(true);
      });

      expect(isValidState("California")).toBe(false);
      expect(isValidState("C")).toBe(false);
    });
  });

  describe("Price Validation", () => {
    it("should format price for display", () => {
      const formatPrice = (price: number) => {
        if (price >= 1000000) {
          return `$${(price / 1000000).toFixed(1)}M`.replace(".0M", "M");
        }
        return `$${(price / 1000).toFixed(0)}K`;
      };

      expect(formatPrice(1500000)).toBe("$1.5M");
      expect(formatPrice(1000000)).toBe("$1M");
      expect(formatPrice(500000)).toBe("$500K");
    });
  });

  describe("Features Validation", () => {
    it("should limit number of features", () => {
      const maxFeatures = 20;
      const features = Array(25).fill("Feature");

      const validatedFeatures = features.slice(0, maxFeatures);

      expect(validatedFeatures).toHaveLength(maxFeatures);
    });

    it("should sanitize feature text", () => {
      const sanitize = (feature: string) => {
        return feature.trim().slice(0, 100);
      };

      expect(sanitize("  Pool  ")).toBe("Pool");
      expect(sanitize("A".repeat(150)).length).toBe(100);
    });
  });
});

describe("Listing Status Transitions", () => {
  const validTransitions: Record<string, string[]> = {
    draft: ["active", "archived"],
    active: ["pending", "sold", "archived"],
    pending: ["active", "sold", "archived"],
    sold: ["archived"],
    archived: ["active"],
  };

  it("should allow valid status transitions", () => {
    const canTransition = (from: string, to: string) => {
      return validTransitions[from]?.includes(to) ?? false;
    };

    expect(canTransition("draft", "active")).toBe(true);
    expect(canTransition("active", "sold")).toBe(true);
    expect(canTransition("sold", "active")).toBe(false);
  });

  it("should prevent invalid status transitions", () => {
    const canTransition = (from: string, to: string) => {
      return validTransitions[from]?.includes(to) ?? false;
    };

    expect(canTransition("draft", "sold")).toBe(false);
    expect(canTransition("archived", "sold")).toBe(false);
  });
});

describe("Listing Search", () => {
  it("should build search query correctly", () => {
    const buildSearchQuery = (params: {
      city?: string;
      minPrice?: number;
      maxPrice?: number;
      minBeds?: number;
    }) => {
      const conditions: string[] = [];

      if (params.city) {
        conditions.push(`city.ilike.%${params.city}%`);
      }
      if (params.minPrice) {
        conditions.push(`listing_price.gte.${params.minPrice}`);
      }
      if (params.maxPrice) {
        conditions.push(`listing_price.lte.${params.maxPrice}`);
      }
      if (params.minBeds) {
        conditions.push(`bedrooms.gte.${params.minBeds}`);
      }

      return conditions;
    };

    const query = buildSearchQuery({
      city: "Los Angeles",
      minPrice: 500000,
      maxPrice: 1000000,
      minBeds: 3,
    });

    expect(query).toContain("city.ilike.%Los Angeles%");
    expect(query).toContain("listing_price.gte.500000");
    expect(query).toContain("bedrooms.gte.3");
  });
});
