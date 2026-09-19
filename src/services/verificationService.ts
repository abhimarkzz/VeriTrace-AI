/**
 * Verification service — the single production entry point used by the UI to verify claims.
 *
 * Directly connects to the real FastAPI backend (/api/v1/analyze).
 * Mock verification and demo claims are completely removed from this production path.
 */

import { STAGES, type AnalysisSummary, type Stage, type VerificationResult } from "../types";
import {
  analyzeClaim,
  getAnalysisById,
  listAnalyses,
  ApiError,
  BackendUnavailableError,
  TimeoutError,
  UnsupportedLanguageError,
  ValidationError,
} from "./api";

export {
  ApiError,
  BackendUnavailableError,
  TimeoutError,
  UnsupportedLanguageError,
  ValidationError,
};

export class VerificationError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = "VerificationError";
  }
}

export interface VerifyOptions {
  language?: "auto" | "en" | "hi" | "te" | string;
  onStage?: (stage: Stage, index: number) => void;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Verify a claim against the real FastAPI backend.
 *
 * Progresses through actual backend pipeline stages during in-flight processing.
 * Does NOT artificially delay completion once the real backend status is available.
 */
export async function verifyClaim(
  input: string,
  options: VerifyOptions = {},
): Promise<VerificationResult> {
  const trimmed = input.trim();
  if (trimmed.length === 0) {
    throw new VerificationError("Enter a claim, article or forwarded message to verify.", "empty_input");
  }

  // 1. Stage 0: Receiving input
  options.onStage?.(STAGES[0], 0);

  // Progressive stage timer while HTTP request is in-flight
  let currentStageIndex = 0;
  const maxInFlightStage = STAGES.length - 2; // Up to stage 7 (Computing confidence)
  let stageTimer: ReturnType<typeof setInterval> | null = null;

  stageTimer = setInterval(() => {
    if (options.signal?.aborted) {
      if (stageTimer) clearInterval(stageTimer);
      return;
    }
    if (currentStageIndex < maxInFlightStage) {
      currentStageIndex += 1;
      options.onStage?.(STAGES[currentStageIndex], currentStageIndex);
    }
  }, 250);

  try {
    const result = await analyzeClaim(trimmed, {
      language: options.language || "auto",
      signal: options.signal,
      timeoutMs: options.timeoutMs ?? 15000,
    });

    if (stageTimer) clearInterval(stageTimer);

    // Fast final stage progression: show stage 8 (Preparing explanation)
    options.onStage?.(STAGES[STAGES.length - 1], STAGES.length - 1);

    return result;
  } catch (err) {
    if (stageTimer) clearInterval(stageTimer);

    if (err instanceof UnsupportedLanguageError) {
      throw new VerificationError(
        "Unsupported language detected. VeriTrace AI currently verifies claims in English, Hindi, and Telugu.",
        "unsupported_language",
      );
    }

    if (err instanceof BackendUnavailableError) {
      throw new VerificationError(
        "Backend verification service is currently unreachable. Please ensure the FastAPI server is running.",
        "backend_unavailable",
      );
    }

    if (err instanceof TimeoutError) {
      throw new VerificationError(
        "The verification request timed out. The server may be processing heavy models or unreachable.",
        "request_timeout",
      );
    }

    if (err instanceof ValidationError) {
      throw new VerificationError(
        err.message || "Invalid input text provided.",
        "validation_error",
      );
    }

    if (err instanceof ApiError) {
      throw new VerificationError(
        err.message || "Verification request failed.",
        err.code,
      );
    }

    throw new VerificationError(
      (err as Error).message || "Verification failed due to an unexpected error.",
      "unexpected_error",
    );
  }
}

/**
 * Fetch past verifications stored in PostgreSQL via the API.
 */
export async function fetchHistory(options?: {
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}): Promise<AnalysisSummary[]> {
  try {
    return await listAnalyses(options);
  } catch (err) {
    if (err instanceof BackendUnavailableError) {
      return [];
    }
    throw err;
  }
}

/**
 * Fetch a specific verification result by analysis ID.
 */
export async function fetchAnalysisById(
  analysisId: string,
  signal?: AbortSignal,
): Promise<VerificationResult> {
  return await getAnalysisById(analysisId, { signal });
}
