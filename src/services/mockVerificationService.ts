/**
 * DEVELOPMENT AND TEST FIXTURE ONLY
 *
 * This mock verification service is strictly preserved for unit tests
 * (e.g. mockVerificationService.test.ts) and is REMOVED from the production
 * verification path. Production uses src/services/verificationService.ts.
 */

import { SCENARIOS, UNKNOWN_CLAIM_RESULT } from "../mock/demoClaims";
import { STAGES, type Stage, type VerificationResult } from "../types";

// Tuned so tests and offline demonstrations can walk through the 9 stages if needed.
const STAGE_DURATIONS: Record<Stage, number> = {
  "Receiving input": 100,
  "Detecting language": 100,
  "Extracting claims": 100,
  "Running multilingual model": 100,
  "Retrieving evidence": 100,
  "Ranking evidence": 100,
  "Verifying evidence": 100,
  "Computing confidence": 100,
  "Preparing explanation": 100,
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
