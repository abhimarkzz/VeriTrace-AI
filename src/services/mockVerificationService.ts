import { SCENARIOS, UNKNOWN_CLAIM_RESULT } from "../mock/demoClaims";
import { STAGES, type Stage, type VerificationResult } from "../types";

// Tuned so the pipeline reads as deliberate work rather than a stalled page.
const STAGE_DURATIONS: Record<Stage, number> = {
  "Detecting language": 500,
  "Extracting claim": 700,
  "Understanding claim": 600,
  "Searching for evidence": 1200,
  "Comparing evidence": 900,
  "Generating assessment": 600,
};

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function normalise(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

/** Deterministic: the same input always resolves to the same scenario. */
export function matchScenario(input: string): VerificationResult {
  const haystack = normalise(input);

  const scored = SCENARIOS.map((scenario) => ({
    scenario,
    hits: scenario.matchKeywords.filter((kw) => haystack.includes(normalise(kw))).length,
  }));

  scored.sort((a, b) => b.hits - a.hits);
  const best = scored[0];

  if (!best || best.hits < 2) {
    return { ...UNKNOWN_CLAIM_RESULT, claim: input.trim() };
  }
  return best.scenario.result;
}

export interface VerifyOptions {
  onStage?: (stage: Stage, index: number) => void;
  signal?: AbortSignal;
}

export class VerificationError extends Error {}

export async function verifyClaim(
  input: string,
  options: VerifyOptions = {}
): Promise<VerificationResult> {
  if (input.trim().length === 0) {
    throw new VerificationError("Enter a claim, article or message to verify.");
  }

  for (const [index, stage] of STAGES.entries()) {
    if (options.signal?.aborted) {
      throw new VerificationError("Verification cancelled.");
    }
    options.onStage?.(stage, index);
    await delay(STAGE_DURATIONS[stage]);
  }

  return matchScenario(input);
}
