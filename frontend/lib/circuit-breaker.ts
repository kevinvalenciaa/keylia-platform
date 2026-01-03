/**
 * Circuit Breaker Pattern Implementation
 *
 * Prevents cascading failures by stopping calls to failing services.
 * States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing)
 *
 * @example
 * const breaker = new CircuitBreaker("anthropic", { failureThreshold: 5 });
 * const result = await breaker.call(() => anthropic.messages.create({...}));
 */

export type CircuitState = "CLOSED" | "OPEN" | "HALF_OPEN";

export interface CircuitBreakerOptions {
  /** Number of failures before opening circuit (default: 5) */
  failureThreshold?: number;
  /** Time in ms before attempting recovery (default: 60000 = 1 min) */
  recoveryTimeout?: number;
  /** Number of successful calls in HALF_OPEN to close circuit (default: 2) */
  successThreshold?: number;
  /** Timeout for individual calls in ms (default: 30000 = 30s) */
  callTimeout?: number;
  /** Called when circuit opens */
  onOpen?: (name: string, error: Error) => void;
  /** Called when circuit closes */
  onClose?: (name: string) => void;
  /** Called when circuit enters half-open */
  onHalfOpen?: (name: string) => void;
}

export interface CircuitBreakerStats {
  state: CircuitState;
  failures: number;
  successes: number;
  lastFailureTime: number | null;
  totalCalls: number;
  totalFailures: number;
  totalSuccesses: number;
}

export class CircuitBreakerError extends Error {
  constructor(
    message: string,
    public readonly circuitName: string,
    public readonly state: CircuitState
  ) {
    super(message);
    this.name = "CircuitBreakerError";
  }
}

export class CircuitBreaker {
  private state: CircuitState = "CLOSED";
  private failures = 0;
  private successes = 0;
  private lastFailureTime: number | null = null;
  private totalCalls = 0;
  private totalFailures = 0;
  private totalSuccesses = 0;

  private readonly failureThreshold: number;
  private readonly recoveryTimeout: number;
  private readonly successThreshold: number;
  private readonly callTimeout: number;
  private readonly onOpen?: (name: string, error: Error) => void;
  private readonly onClose?: (name: string) => void;
  private readonly onHalfOpen?: (name: string) => void;

  constructor(
    private readonly name: string,
    options: CircuitBreakerOptions = {}
  ) {
    this.failureThreshold = options.failureThreshold ?? 5;
    this.recoveryTimeout = options.recoveryTimeout ?? 60000;
    this.successThreshold = options.successThreshold ?? 2;
    this.callTimeout = options.callTimeout ?? 30000;
    this.onOpen = options.onOpen;
    this.onClose = options.onClose;
    this.onHalfOpen = options.onHalfOpen;
  }

  /**
   * Execute a function through the circuit breaker.
   * Throws CircuitBreakerError if circuit is open.
   */
  async call<T>(fn: () => Promise<T>): Promise<T> {
    this.totalCalls++;

    // Check if we should attempt recovery
    if (this.state === "OPEN") {
      if (this.shouldAttemptRecovery()) {
        this.transitionTo("HALF_OPEN");
      } else {
        throw new CircuitBreakerError(
          `Circuit breaker "${this.name}" is OPEN. Service temporarily unavailable.`,
          this.name,
          this.state
        );
      }
    }

    try {
      const result = await this.executeWithTimeout(fn);
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error as Error);
      throw error;
    }
  }

  /**
   * Execute function with timeout protection.
   */
  private async executeWithTimeout<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Circuit breaker "${this.name}" call timed out after ${this.callTimeout}ms`));
      }, this.callTimeout);

      fn()
        .then((result) => {
          clearTimeout(timeoutId);
          resolve(result);
        })
        .catch((error) => {
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }

  /**
   * Handle successful call.
   */
  private onSuccess(): void {
    this.totalSuccesses++;

    if (this.state === "HALF_OPEN") {
      this.successes++;
      if (this.successes >= this.successThreshold) {
        this.transitionTo("CLOSED");
      }
    } else if (this.state === "CLOSED") {
      // Reset failure count on success in closed state
      this.failures = 0;
    }
  }

  /**
   * Handle failed call.
   */
  private onFailure(error: Error): void {
    this.totalFailures++;
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.state === "HALF_OPEN") {
      // Any failure in half-open goes back to open
      this.transitionTo("OPEN", error);
    } else if (this.state === "CLOSED" && this.failures >= this.failureThreshold) {
      this.transitionTo("OPEN", error);
    }
  }

  /**
   * Check if enough time has passed to attempt recovery.
   */
  private shouldAttemptRecovery(): boolean {
    if (!this.lastFailureTime) return true;
    return Date.now() - this.lastFailureTime >= this.recoveryTimeout;
  }

  /**
   * Transition to a new state.
   */
  private transitionTo(newState: CircuitState, error?: Error): void {
    const previousState = this.state;
    this.state = newState;

    // Reset counters on state change
    if (newState === "CLOSED") {
      this.failures = 0;
      this.successes = 0;
      this.onClose?.(this.name);
      console.log(`[CircuitBreaker] ${this.name}: ${previousState} -> CLOSED (recovered)`);
    } else if (newState === "OPEN") {
      this.successes = 0;
      this.onOpen?.(this.name, error!);
      console.warn(`[CircuitBreaker] ${this.name}: ${previousState} -> OPEN (failures: ${this.failures})`);
    } else if (newState === "HALF_OPEN") {
      this.successes = 0;
      this.onHalfOpen?.(this.name);
      console.log(`[CircuitBreaker] ${this.name}: ${previousState} -> HALF_OPEN (attempting recovery)`);
    }
  }

  /**
   * Get current circuit breaker statistics.
   */
  getStats(): CircuitBreakerStats {
    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      lastFailureTime: this.lastFailureTime,
      totalCalls: this.totalCalls,
      totalFailures: this.totalFailures,
      totalSuccesses: this.totalSuccesses,
    };
  }

  /**
   * Manually reset the circuit breaker to CLOSED state.
   * Use with caution - typically for testing or manual intervention.
   */
  reset(): void {
    this.state = "CLOSED";
    this.failures = 0;
    this.successes = 0;
    this.lastFailureTime = null;
    console.log(`[CircuitBreaker] ${this.name}: Manually reset to CLOSED`);
  }

  /**
   * Check if circuit is currently allowing calls.
   */
  isAvailable(): boolean {
    if (this.state === "CLOSED") return true;
    if (this.state === "HALF_OPEN") return true;
    if (this.state === "OPEN" && this.shouldAttemptRecovery()) return true;
    return false;
  }

  /**
   * Get the current state.
   */
  getState(): CircuitState {
    return this.state;
  }
}

/**
 * Global registry for circuit breakers.
 * Allows sharing circuit breakers across modules.
 */
class CircuitBreakerRegistry {
  private breakers = new Map<string, CircuitBreaker>();

  /**
   * Get or create a circuit breaker by name.
   */
  get(name: string, options?: CircuitBreakerOptions): CircuitBreaker {
    let breaker = this.breakers.get(name);
    if (!breaker) {
      breaker = new CircuitBreaker(name, options);
      this.breakers.set(name, breaker);
    }
    return breaker;
  }

  /**
   * Get all circuit breaker stats.
   */
  getAllStats(): Record<string, CircuitBreakerStats> {
    const stats: Record<string, CircuitBreakerStats> = {};
    this.breakers.forEach((breaker, name) => {
      stats[name] = breaker.getStats();
    });
    return stats;
  }

  /**
   * Reset all circuit breakers.
   */
  resetAll(): void {
    this.breakers.forEach((breaker) => {
      breaker.reset();
    });
  }
}

export const circuitBreakerRegistry = new CircuitBreakerRegistry();

/**
 * Pre-configured circuit breakers for common services.
 */
export const circuitBreakers = {
  anthropic: circuitBreakerRegistry.get("anthropic", {
    failureThreshold: 3,
    recoveryTimeout: 60000,
    successThreshold: 2,
    callTimeout: 120000, // 2 minutes for AI calls
    onOpen: (name, error) => {
      console.error(`[AI Service] ${name} circuit opened:`, error.message);
    },
  }),

  stripe: circuitBreakerRegistry.get("stripe", {
    failureThreshold: 5,
    recoveryTimeout: 30000,
    successThreshold: 2,
    callTimeout: 30000,
    onOpen: (name, error) => {
      console.error(`[Billing] ${name} circuit opened:`, error.message);
    },
  }),

  backend: circuitBreakerRegistry.get("backend", {
    failureThreshold: 5,
    recoveryTimeout: 30000,
    successThreshold: 3,
    callTimeout: 60000,
    onOpen: (name, error) => {
      console.error(`[Backend API] ${name} circuit opened:`, error.message);
    },
  }),
};
