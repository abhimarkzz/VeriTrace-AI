/**
 * VeriTrace API Client
 *
 * Robust, typed HTTP client for communicating with the FastAPI backend.
 * Handles timeouts, network failure detection, and structured API errors.
 */

// Read base URL from environment (supporting VITE_API_BASE_URL or VITE_API_URL fallback)
const rawBase =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  (import.meta.env.VITE_API_URL as string | undefined) ||
  "";

export const API_BASE_URL = rawBase.replace(/\/+$/, "");

/**
 * Base structured error thrown by VeriTrace API calls.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string = "api_error",
    public readonly body?: unknown,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Thrown when the backend server is unreachable (offline, connection refused, DNS failure).
 */
export class BackendUnavailableError extends ApiError {
  constructor(message = "Backend verification service is currently unreachable. Please ensure the VeriTrace server is running.") {
    super(message, 0, "backend_unavailable");
    this.name = "BackendUnavailableError";
  }
}

/**
 * Thrown when an API request exceeds the configured timeout threshold.
 */
export class TimeoutError extends ApiError {
  constructor(message = "The verification request timed out. Please try again.") {
    super(message, 408, "request_timeout");
    this.name = "TimeoutError";
  }
}

/**
 * Thrown when input language is not currently supported by VeriTrace.
 */
export class UnsupportedLanguageError extends ApiError {
  constructor(message = "Unsupported language detected. VeriTrace AI currently verifies claims in English, Hindi, and Telugu.") {
    super(message, 400, "unsupported_language");
    this.name = "UnsupportedLanguageError";
  }
}

/**
 * Thrown when the input fails schema validation.
 */
export class ValidationError extends ApiError {
  constructor(message = "Input text failed validation. Please provide non-empty text.", body?: unknown) {
    super(message, 422, "validation_error", body);
    this.name = "ValidationError";
  }
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Execute a typed HTTP request against the VeriTrace backend API.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, signal, timeoutMs = 15000 } = options;

  // Build target URL
  const url = path.startsWith("http://") || path.startsWith("https://")
    ? path
    : `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;

  // Configure timeout controller linked with optional caller signal
  const timeoutController = new AbortController();
  let timedOut = false;

  const timer = setTimeout(() => {
    timedOut = true;
    timeoutController.abort();
  }, timeoutMs);

  const mergedSignal = signal
    ? createCombinedSignal([signal, timeoutController.signal])
    : timeoutController.signal;

  const init: RequestInit = {
    method,
    signal: mergedSignal,
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  };

  try {
    const response = await fetch(url, init);
    clearTimeout(timer);

    const requestId = response.headers.get("X-Request-ID") || undefined;

    if (!response.ok) {
      let errBody: Record<string, unknown> | string | undefined;
      try {
        errBody = await response.json();
      } catch {
        errBody = await response.text().catch(() => undefined);
      }

      const detail = typeof errBody === "object" && errBody !== null ? (errBody as Record<string, unknown>).detail : undefined;
      const errorCode = typeof detail === "object" && detail !== null
        ? String((detail as Record<string, unknown>).error || "")
        : typeof errBody === "object" && errBody !== null
        ? String((errBody as Record<string, unknown>).error || "")
        : "";
      const errorMessage = typeof detail === "object" && detail !== null
        ? String((detail as Record<string, unknown>).message || "")
        : typeof errBody === "object" && errBody !== null
        ? String((errBody as Record<string, unknown>).message || "")
        : typeof errBody === "string"
        ? errBody
        : `Request failed with HTTP status ${response.status}`;

      if (errorCode === "unsupported_language" || errorMessage.toLowerCase().includes("unsupported language")) {
        throw new UnsupportedLanguageError(errorMessage);
      }

      if (response.status === 422) {
        throw new ValidationError(errorMessage, errBody);
      }

      throw new ApiError(
        errorMessage || `API request failed with status ${response.status}`,
        response.status,
        errorCode || `http_${response.status}`,
        errBody,
        requestId,
      );
    }

    return (await response.json()) as T;
  } catch (err) {
    clearTimeout(timer);

    if (err instanceof ApiError) {
      throw err;
    }

    if (timedOut) {
      throw new TimeoutError();
    }

    if (err instanceof DOMException && err.name === "AbortError") {
      if (signal?.aborted) {
        throw new ApiError("Request was cancelled", 0, "request_cancelled");
      }
      throw new TimeoutError();
    }

    if (err instanceof TypeError) {
      // Network failure, refused connection, offline
      throw new BackendUnavailableError(
        `Backend verification service is currently unreachable (${err.message}). Ensure the FastAPI server is running.`,
      );
    }

    throw new ApiError((err as Error).message || "An unknown network error occurred.", 0, "network_error");
  }
}

/**
 * Check backend health status on GET /api/v1/health.
 */
export async function checkBackendHealth(): Promise<{ ok: boolean; status?: string; error?: string }> {
  try {
    const res = await apiFetch<{ status: string }>("/api/v1/health", { method: "GET", timeoutMs: 3000 });
    return { ok: res.status === "ok", status: res.status };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

/**
 * Helper to combine multiple AbortSignals.
 */
function createCombinedSignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort();
      return controller.signal;
    }
    sig.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller.signal;
}
