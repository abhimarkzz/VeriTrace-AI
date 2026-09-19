import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  verifyClaim,
  VerificationError,
} from "../services/verificationService";
import { STAGES } from "../types";

describe("verificationService production flow", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("throws VerificationError on empty input", async () => {
    await expect(verifyClaim("   ")).rejects.toThrow(VerificationError);
    await expect(verifyClaim("")).rejects.toThrow("Enter a claim, article or forwarded message");
  });

  it("executes successful verification flow and triggers backend stages", async () => {
    const mockBackendResponse = {
      analysis_id: "flow-123",
      language: "en",
      claim: "NASA confirmed liquid water discovered on Mars.",
      claim_type: "Scientific discovery claim",
      assessment: "SUPPORTED",
      confidence: 0.91,
      confidence_tier: "HIGH CONFIDENCE",
      confidence_explanation: "High confidence with multiple independent scientific publications.",
      confidence_breakdown: {
        evidence_agreement: 0.96,
        evidence_relevance: 0.92,
        source_quality: 0.90,
        model_confidence: 0.88,
      },
      evidence_strength: "STRONG",
      evidence: [
        {
          id: "ev-01",
          title: "NASA Confirms Evidence That Liquid Water Flows on Today's Mars",
          source: "NASA",
          publisher: "NASA Science",
          url: "https://www.nasa.gov/news/water-on-mars",
          snippet: "New findings from NASA's Mars Reconnaissance Orbiter provide strongest evidence yet...",
          relevance_score: 0.95,
          source_quality: 0.98,
          relation: "SUPPORT",
          published_at: "2015-09-28T15:30:00Z",
        },
      ],
      explanation: "Multiple scientific sources confirm the observation of hydrated salts on recurring slope lineae.",
      pipeline_status: "completed",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => mockBackendResponse,
    } as unknown as Response);

    const stagesVisited: string[] = [];
    const outcome = await verifyClaim("NASA confirmed liquid water discovered on Mars.", {
      language: "en",
      onStage: (stage, _index) => {
        stagesVisited.push(stage);
      },
    });

    expect(outcome.assessment).toBe("SUPPORTED");
    expect(outcome.claim).toBe(mockBackendResponse.claim);
    expect(outcome.confidence).toBe(0.91);
    expect(outcome.confidenceTier).toBe("HIGH CONFIDENCE");
    expect(outcome.evidence.length).toBe(1);
    expect(outcome.evidence[0].source).toBe("NASA Science");
    expect(stagesVisited.length).toBeGreaterThan(0);
    expect(stagesVisited[0]).toBe(STAGES[0]); // Receiving input
    expect(stagesVisited).toContain(STAGES[STAGES.length - 1]); // Preparing explanation
  });

  it("handles conflicting evidence verdict from real backend", async () => {
    const mockConflictResponse = {
      analysis_id: "conflict-456",
      language: "en",
      claim: "Study says moderate coffee consumption extends lifespan.",
      claim_type: "Observational health claim",
      assessment: "CONFLICTING_EVIDENCE",
      confidence: 0.55,
      confidence_tier: "MODERATE CONFIDENCE",
      confidence_explanation: "Independent studies present irreconcilable conclusions.",
      evidence_strength: "MODERATE",
      evidence: [
        {
          id: "ev-01",
          title: "Coffee consumption linked to reduced mortality",
          source: "New England Journal of Medicine",
          url: "https://nejm.org/coffee",
          snippet: "Significant inverse association observed between coffee consumption and all-cause mortality.",
          relevance_score: 0.88,
          source_quality: 0.92,
          relation: "SUPPORT",
        },
        {
          id: "ev-02",
          title: "No causal longevity benefit found from coffee intake",
          source: "British Medical Journal",
          url: "https://bmj.com/coffee-mortality",
          snippet: "Mendelian randomization showed no causal effect on lifespan.",
          relevance_score: 0.85,
          source_quality: 0.90,
          relation: "CONTRADICT",
        },
      ],
      explanation: "Observational and genetic studies reach contradictory conclusions regarding causation.",
      pipeline_status: "completed",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => mockConflictResponse,
    } as unknown as Response);

    const outcome = await verifyClaim("Study says moderate coffee consumption extends lifespan.");
    expect(outcome.assessment).toBe("CONFLICTING_EVIDENCE");
    expect(outcome.evidence.length).toBe(2);
    expect(outcome.evidence[0].relation).toBe("SUPPORT");
    expect(outcome.evidence[1].relation).toBe("CONTRADICT");
  });

  it("handles zero evidence (INSUFFICIENT_EVIDENCE) honestly", async () => {
    const mockEmptyResponse = {
      analysis_id: "empty-789",
      language: "te",
      claim: "ఏ ఆధారాలు లేని గుర్తుతెలియని ప్రకటన.",
      assessment: "INSUFFICIENT_EVIDENCE",
      confidence: null,
      confidence_tier: "LOW CONFIDENCE",
      confidence_explanation: "No verifiable external citations found.",
      evidence_strength: null,
      evidence: [],
      explanation: "No evidence sources found. VeriTrace restricts certainty to Insufficient Evidence.",
      pipeline_status: "completed",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => mockEmptyResponse,
    } as unknown as Response);

    const outcome = await verifyClaim("ఏ ఆధారాలు లేని గుర్తుతెలియని ప్రకటన.", { language: "te" });
    expect(outcome.assessment).toBe("INSUFFICIENT_EVIDENCE");
    expect(outcome.confidence).toBeNull();
    expect(outcome.confidenceTier).toBe("LOW CONFIDENCE");
    expect(outcome.evidence).toEqual([]);
  });

  it("maps backend unavailable (TypeError) to descriptive VerificationError", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(verifyClaim("Some claim to check")).rejects.toThrow(
      /Backend verification service is currently unreachable/i,
    );
  });

  it("maps unsupported language error to clear VerificationError", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers(),
      json: async () => ({
        detail: {
          error: "unsupported_language",
          message: "Language 'es' is not supported.",
        },
      }),
    } as unknown as Response);

    await expect(verifyClaim("El sol gira alrededor de la tierra", { language: "es" })).rejects.toThrow(
      /Unsupported language detected/i,
    );
  });
});
