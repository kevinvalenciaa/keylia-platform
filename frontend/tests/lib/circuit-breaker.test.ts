/**
 * Circuit Breaker Tests
 *
 * Comprehensive tests for the circuit breaker pattern implementation
 * to ensure reliability in production.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  CircuitBreaker,
  CircuitBreakerError,
  circuitBreakerRegistry,
} from "@/lib/circuit-breaker";

describe("CircuitBreaker", () => {
  let breaker: CircuitBreaker;

  beforeEach(() => {
    breaker = new CircuitBreaker("test", {
      failureThreshold: 3,
      recoveryTimeout: 1000,
      successThreshold: 2,
      callTimeout: 100,
    });
  });

  describe("CLOSED state (normal operation)", () => {
    it("allows successful calls", async () => {
      const result = await breaker.call(async () => "success");
      expect(result).toBe("success");
      expect(breaker.getState()).toBe("CLOSED");
    });

    it("tracks successes and failures", async () => {
      await breaker.call(async () => "ok");
      const stats = breaker.getStats();
      expect(stats.totalCalls).toBe(1);
      expect(stats.totalSuccesses).toBe(1);
      expect(stats.totalFailures).toBe(0);
    });

    it("resets failure count on success", async () => {
      // Cause some failures (but not enough to open)
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      // Success should reset
      await breaker.call(async () => "success");

      // Two more failures should not open the circuit
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      expect(breaker.getState()).toBe("CLOSED");
    });
  });

  describe("OPEN state (failure mode)", () => {
    it("opens after failure threshold is reached", async () => {
      // Cause enough failures to open
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error(`fail ${i}`);
          });
        } catch {}
      }

      expect(breaker.getState()).toBe("OPEN");
    });

    it("rejects calls when open", async () => {
      // Force open state
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      // Next call should throw CircuitBreakerError
      await expect(breaker.call(async () => "never")).rejects.toThrow(
        CircuitBreakerError
      );
    });

    it("provides helpful error message when open", async () => {
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      try {
        await breaker.call(async () => "never");
      } catch (error) {
        expect(error).toBeInstanceOf(CircuitBreakerError);
        expect((error as CircuitBreakerError).circuitName).toBe("test");
        expect((error as CircuitBreakerError).state).toBe("OPEN");
      }
    });
  });

  describe("HALF_OPEN state (recovery)", () => {
    it("transitions to HALF_OPEN after recovery timeout", async () => {
      vi.useFakeTimers();

      // Open the circuit
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      expect(breaker.getState()).toBe("OPEN");

      // Fast forward past recovery timeout
      vi.advanceTimersByTime(1100);

      // Next call should be allowed (HALF_OPEN)
      expect(breaker.isAvailable()).toBe(true);

      vi.useRealTimers();
    });

    it("closes after success threshold in HALF_OPEN", async () => {
      vi.useFakeTimers();

      // Open the circuit
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      // Fast forward past recovery timeout
      vi.advanceTimersByTime(1100);

      // Two successful calls should close
      await breaker.call(async () => "ok");
      await breaker.call(async () => "ok");

      expect(breaker.getState()).toBe("CLOSED");

      vi.useRealTimers();
    });

    it("reopens on failure in HALF_OPEN", async () => {
      vi.useFakeTimers();

      // Open the circuit
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      // Fast forward past recovery timeout
      vi.advanceTimersByTime(1100);

      // Fail in half-open
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      expect(breaker.getState()).toBe("OPEN");

      vi.useRealTimers();
    });
  });

  describe("timeout handling", () => {
    it("times out slow operations", async () => {
      const slowBreaker = new CircuitBreaker("slow", {
        callTimeout: 50,
        failureThreshold: 3,
      });

      await expect(
        slowBreaker.call(
          () => new Promise((resolve) => setTimeout(resolve, 200))
        )
      ).rejects.toThrow(/timed out/);
    });

    it("counts timeouts as failures", async () => {
      const slowBreaker = new CircuitBreaker("slow-count", {
        callTimeout: 10,
        failureThreshold: 2,
      });

      try {
        await slowBreaker.call(
          () => new Promise((resolve) => setTimeout(resolve, 100))
        );
      } catch {}
      try {
        await slowBreaker.call(
          () => new Promise((resolve) => setTimeout(resolve, 100))
        );
      } catch {}

      expect(slowBreaker.getState()).toBe("OPEN");
    });
  });

  describe("callbacks", () => {
    it("calls onOpen when circuit opens", async () => {
      const onOpen = vi.fn();
      const callbackBreaker = new CircuitBreaker("callbacks", {
        failureThreshold: 1,
        onOpen,
      });

      try {
        await callbackBreaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      expect(onOpen).toHaveBeenCalledWith("callbacks", expect.any(Error));
    });

    it("calls onClose when circuit closes", async () => {
      vi.useFakeTimers();

      const onClose = vi.fn();
      const callbackBreaker = new CircuitBreaker("close-callbacks", {
        failureThreshold: 1,
        recoveryTimeout: 100,
        successThreshold: 1,
        onClose,
      });

      // Open circuit
      try {
        await callbackBreaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      // Wait for recovery
      vi.advanceTimersByTime(200);

      // Close with success
      await callbackBreaker.call(async () => "ok");

      expect(onClose).toHaveBeenCalledWith("close-callbacks");

      vi.useRealTimers();
    });
  });

  describe("reset()", () => {
    it("manually resets circuit to CLOSED", async () => {
      // Open the circuit
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.call(async () => {
            throw new Error("fail");
          });
        } catch {}
      }

      expect(breaker.getState()).toBe("OPEN");

      breaker.reset();

      expect(breaker.getState()).toBe("CLOSED");
      expect(breaker.isAvailable()).toBe(true);
    });
  });

  describe("getStats()", () => {
    it("returns comprehensive statistics", async () => {
      await breaker.call(async () => "ok");
      try {
        await breaker.call(async () => {
          throw new Error("fail");
        });
      } catch {}

      const stats = breaker.getStats();
      expect(stats).toMatchObject({
        state: "CLOSED",
        totalCalls: 2,
        totalSuccesses: 1,
        totalFailures: 1,
      });
    });
  });
});

describe("CircuitBreakerRegistry", () => {
  it("returns same breaker for same name", () => {
    const breaker1 = circuitBreakerRegistry.get("shared");
    const breaker2 = circuitBreakerRegistry.get("shared");

    expect(breaker1).toBe(breaker2);
  });

  it("creates different breakers for different names", () => {
    const breaker1 = circuitBreakerRegistry.get("unique1");
    const breaker2 = circuitBreakerRegistry.get("unique2");

    expect(breaker1).not.toBe(breaker2);
  });

  it("returns stats for all breakers", () => {
    circuitBreakerRegistry.get("stats1");
    circuitBreakerRegistry.get("stats2");

    const allStats = circuitBreakerRegistry.getAllStats();
    expect(allStats).toHaveProperty("stats1");
    expect(allStats).toHaveProperty("stats2");
  });
});
