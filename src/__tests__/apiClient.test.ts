import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  apiFetch,
  checkBackendHealth,
  ApiError,
  BackendUnavailableError,
  TimeoutError,
  UnsupportedLanguageError,
  ValidationError,
} from "../services/api/client";
import {
  mapBackendResponseToVerificationResult,
  analyzeClaim,
  getAnalysisById,
  type BackendAnalysisResponse,
} from "../services/api/analysis";

describe("apiClient", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("sends POST request with JSON headers and parses JSON response", async () => {
    const mockData = { status: "ok", test: 123 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "X-Request-ID": "req-123" }),
      json: async () => mockData,
    } as unknown as Response);

    const result = await apiFetch<typeof mockData>("/api/v1/test", {
      method: "POST",
      body: { query: "hello" },
    });

    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/v1/test");
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ query: "hello" });
  });

  it("throws BackendUnavailableError on network failure (TypeError)", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(BackendUnavailableError);
  });

  it("throws TimeoutError when request times out", async () => {
    globalThis.fetch = vi.fn().mockImplementation(
      () =>
        new Promise((_, reject) => {
          setTimeout(() => {
            const err = new DOMException("The operation was aborted.", "AbortError");
            reject(err);
          }, 50);
        }),
    );

    await expect(apiFetch("/api/v1/test", { timeoutMs: 20 })).rejects.toThrow(TimeoutError);
  });

  it("throws UnsupportedLanguageError when backend returns unsupported_language", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers(),
      json: async () => ({
        detail: {
          error: "unsupported_language",
          message: "Language 'fr' is not supported.",
        },
      }),
    } as unknown as Response);

    await expect(apiFetch("/api/v1/analyze", { method: "POST", body: {} })).rejects.toThrow(
      UnsupportedLanguageError,
    );
  });

  it("throws ValidationError on 422 status", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: new Headers(),
      json: async () => ({
        detail: [{ loc: ["body", "text"], msg: "field required" }],
      }),
    } as unknown as Response);

    await expect(apiFetch("/api/v1/analyze", { method: "POST", body: {} })).rejects.toThrow(
      ValidationError,
    );
  });

  it("throws ApiError with HTTP status on general server errors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers({ "X-Request-ID": "err-500" }),
      json: async () => ({
        detail: { error: "internal_error", message: "Database connection failed" },
      }),
    } as unknown as Response);

    await expect(apiFetch("/api/v1/analyze", { method: "POST" })).rejects.toThrow(ApiError);
  });

  it("checkBackendHealth returns ok true when /api/v1/health responds ok", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => ({ status: "ok" }),
    } as unknown as Response);

    const health = await checkBackendHealth();
    expect(health.ok).toBe(true);
    expect(health.status).toBe("ok");
  });
});

describe("analysisService mapping", () => {
  it("maps complete backend response to VerificationResult with evidence and calibration", () => {
    const backendData: BackendAnalysisResponse = {
      analysis_id: "test-id-123",
      language: "en",
      claim: "WHO recommends R21 malaria vaccine for children.",
      claim_type: "Medical recommendation claim",
      assessment: "SUPPORTED",
      confidence: 0.88,
      confidence_tier: "HIGH CONFIDENCE",
      confidence_explanation: "High confidence supported by multiple independent sources.",
      confidence_breakdown: {
        evidence_agreement: 0.95,
        evidence_relevance: 0.90,
        source_quality: 0.85,
        model_confidence: 0.92,
      },
      evidence_strength: "STRONG",
      evidence: [
        {
          id: "ev-001",
          title: "WHO recommends R21/Matrix-M vaccine for malaria prevention",
          source: "World Health Organization",
          publisher: "WHO Press",
          url: "https://www.who.int/news/item/02-10-2023-who-recommends-r21",
          snippet: "The WHO has recommended the R21/Matrix-M malaria vaccine...",
          relevance_score: 0.94,
          source_quality: 0.95,
          relation: "SUPPORT",
          published_at: "2023-10-02T12:00:00Z",
        },
      ],
      explanation: "Multiple reliable health authorities confirm this recommendation.",
      pipeline_status: "completed",
    };

    const mapped = mapBackendResponseToVerificationResult(backendData);

    expect(mapped.analysisId).toBe("test-id-123");
    expect(mapped.claim).toBe(backendData.claim);
    expect(mapped.language).toBe("en");
    expect(mapped.claimType).toBe("Medical recommendation claim");
    expect(mapped.assessment).toBe("SUPPORTED");
    expect(mapped.confidence).toBe(0.88);
    expect(mapped.confidenceTier).toBe("HIGH CONFIDENCE");
    expect(mapped.confidenceExplanation).toBe("High confidence supported by multiple independent sources.");
    expect(mapped.evidenceStrength).toBe("STRONG");
    expect(mapped.evidence.length).toBe(1);
    expect(mapped.evidence[0].publisher).toBe("WHO Press");
    expect(mapped.evidence[0].publishedAt).toBe("2023-10-02T12:00:00Z");
    expect(mapped.confidenceBreakdown?.evidenceAgreement).toBe(0.95);
  });

  it("handles null confidence and empty evidence honestly without inventing values", () => {
    const backendData: BackendAnalysisResponse = {
      analysis_id: "no-ev-456",
      language: "hi",
      claim: "अज्ञात दावा जिसकी कोई पुष्टि नहीं है।",
      claim_type: null,
      assessment: "INSUFFICIENT_EVIDENCE",
      confidence: null,
      confidence_tier: "LOW CONFIDENCE",
      confidence_explanation: "No independent evidence was retrieved.",
      confidence_breakdown: null,
      evidence_strength: null,
      evidence: [],
      explanation: "No verifiable citations found.",
      pipeline_status: "completed",
    };

    const mapped = mapBackendResponseToVerificationResult(backendData);

    expect(mapped.assessment).toBe("INSUFFICIENT_EVIDENCE");
    expect(mapped.confidence).toBeNull();
    expect(mapped.confidenceTier).toBe("LOW CONFIDENCE");
    expect(mapped.evidenceStrength).toBeUndefined();
    expect(mapped.evidence).toEqual([]);
    expect(mapped.confidenceBreakdown).toBeUndefined();
  });

  it("analyzeClaim rejects blank input client-side", async () => {
    await expect(analyzeClaim("   ")).rejects.toThrow("Enter a claim");
  });

  it("getAnalysisById calls /api/v1/analysis/{id}", async () => {
    const originalFetch = globalThis.fetch;
    const mockRes = {
      analysis_id: "abc",
      language: "en",
      claim: "test",
      assessment: "SUPPORTED",
      evidence: [],
      explanation: "ok",
      pipeline_status: "completed",
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => mockRes,
    } as unknown as Response);

    const res = await getAnalysisById("abc");
    expect(res.analysisId).toBe("abc");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/analysis/abc"),
      expect.any(Object),
    );

    globalThis.fetch = originalFetch;
  });
});
