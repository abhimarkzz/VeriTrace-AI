import { describe, it, expect } from "vitest";
import { matchScenario } from "../services/mockVerificationService";

describe("matchScenario", () => {
  it("returns a POTENTIALLY_MISLEADING result for the UPI-banned scenario", () => {
    const result = matchScenario(
      "India has banned UPI payments and the service has been shut down nationwide.",
    );
    expect(result.assessment).toBe("POTENTIALLY_MISLEADING");
    expect(result.language).toBe("en");
    expect(result.evidence.length).toBeGreaterThan(0);
  });

  it("returns a SUPPORTED result for the UPI-record scenario", () => {
    const result = matchScenario(
      "UPI processed a record 24.51 billion transactions in August 2026.",
    );
    expect(result.assessment).toBe("SUPPORTED");
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it("returns INSUFFICIENT_EVIDENCE for unrecognised input", () => {
    const result = matchScenario("completely random unrelated text that matches nothing");
    expect(result.assessment).toBe("INSUFFICIENT_EVIDENCE");
    expect(result.confidence).toBeLessThan(0.2);
  });

  it("matches Hindi scenario when Hindi keywords appear", () => {
    const result = matchScenario("UPI से 24.5 अरब से ज्यादा लेनदेन हुए");
    expect(result.assessment).toBe("SUPPORTED");
    expect(result.language).toBe("hi");
  });

  it("matches Telugu scenario when Telugu keywords appear", () => {
    const result = matchScenario("ఆగస్టులో యూపీఐ లావాదేవీల విలువ రూ.29.8 లక్షల కోట్లు");
    expect(result.assessment).toBe("SUPPORTED");
    expect(result.language).toBe("te");
  });
});
