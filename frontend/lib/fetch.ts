/**
 * Fetch utilities with timeout and error handling.
 */

export interface FetchOptions extends RequestInit {
  timeout?: number;
}

export class FetchTimeoutError extends Error {
  constructor(url: string, timeout: number) {
    super(`Request to ${url} timed out after ${timeout}ms`);
    this.name = "FetchTimeoutError";
  }
}

export class FetchError extends Error {
  status: number;
  statusText: string;

  constructor(message: string, status: number, statusText: string) {
    super(message);
    this.name = "FetchError";
    this.status = status;
    this.statusText = statusText;
  }
}

/**
 * Fetch with timeout support.
 *
 * @param url - URL to fetch
 * @param options - Fetch options with optional timeout
 * @returns Promise resolving to Response
 * @throws FetchTimeoutError if request times out
 */
export async function fetchWithTimeout(
  url: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });

    return response;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new FetchTimeoutError(url, timeout);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Fetch JSON with timeout and error handling.
 *
 * @param url - URL to fetch
 * @param options - Fetch options with optional timeout
 * @returns Promise resolving to parsed JSON
 * @throws FetchError if response is not ok
 * @throws FetchTimeoutError if request times out
 */
export async function fetchJson<T>(
  url: string,
  options: FetchOptions = {}
): Promise<T> {
  const response = await fetchWithTimeout(url, options);

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new FetchError(
      `Fetch failed: ${response.status} ${response.statusText} - ${errorBody}`,
      response.status,
      response.statusText
    );
  }

  return response.json() as Promise<T>;
}

/**
 * Default timeout values for different types of requests.
 */
export const TIMEOUTS = {
  /** Default timeout for most API requests (30 seconds) */
  DEFAULT: 30000,

  /** Short timeout for health checks and quick queries (10 seconds) */
  SHORT: 10000,

  /** Extended timeout for AI operations (2 minutes) */
  AI_OPERATION: 120000,

  /** Long timeout for video generation (5 minutes) */
  VIDEO_GENERATION: 300000,
} as const;
