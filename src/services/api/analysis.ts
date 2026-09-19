/**
 * VeriTrace Analysis API Service
 *
 * Implements communication with /api/v1/analyze and /api/v1/analysis/{id}.
 * Maps backend responses cleanly to the frontend VerificationResult model.
 */

import type { Language, VerificationResult, EvidenceItem, Relation } from "../../types";
import { apiFetch } from "./client";

export interface BackendEvidenceItem {
  id: string;
  title: string;
  source: string;
  publisher?: string | null;
  url: string;
  snippet: string;
  relevance_score: number;
  source_quality: number;
  relation: Relation;
  published_at?: string | null;
}

export interface BackendConfidenceBreakdown {
  evidence_agreement?: number | null;
  evidence_relevance?: number | null;
  source_quality?: number | null;
  model_confidence?: number | null;
  probabilities?: Record<string, number> | null;
}

export interface BackendAnalysisResponse {
  analysis_id: string;
  language: string;
  claim: string;
  claim_type?: string | null;
  assessment: VerificationResult["assessment"];
  confidence?: number | null;
  confidence_tier?: string | null;
  confidence_explanation?: string | null;
  confidence_breakdown?: BackendConfidenceBreakdown | null;
  evidence_strength?: VerificationResult["evidenceStrength"] | null;
  evidence: BackendEvidenceItem[];
  explanation: string;
  pipeline_status: "pending" | "running" | "completed" | "failed";
}

export interface AnalyzeOptions {
  language?: "auto" | "en" | "hi" | "te" | string;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Map raw backend analysis response to frontend VerificationResult.
 */
export function mapBackendResponseToVerificationResult(
  data: BackendAnalysisResponse,
): VerificationResult {
  const lang = (["en", "hi", "te"].includes(data.language)
    ? data.language
    : "en") as Language;

  const mappedEvidence: EvidenceItem[] = (data.evidence || []).map((ev) => ({
    id: ev.id,
    title: ev.title,
    source: ev.publisher || ev.source || "Unknown Source",
    publisher: ev.publisher || ev.source || undefined,
    url: ev.url,
    snippet: ev.snippet,
    relevanceScore: ev.relevance_score,
    sourceQuality: ev.source_quality,
    relation: ev.relation,
    publishedAt: ev.published_at || undefined,
  }));

  const bd = data.confidence_breakdown;
  const confidenceBreakdown = bd
    ? {
        evidenceAgreement: bd.evidence_agreement ?? undefined,
        evidenceRelevance: bd.evidence_relevance ?? undefined,
        sourceQuality: bd.source_quality ?? undefined,
        modelConfidence: bd.model_confidence ?? undefined,
        probabilities: bd.probabilities ?? undefined,
      }
    : undefined;

  return {
    analysisId: data.analysis_id,
    claim: data.claim,
    language: lang,
    claimType: data.claim_type || "Factual claim",
    assessment: data.assessment,
    confidence: data.confidence !== undefined ? data.confidence : null,
    confidenceTier: data.confidence_tier || undefined,
    confidenceExplanation: data.confidence_explanation || undefined,
    confidenceBreakdown,
    evidenceStrength: data.evidence_strength || undefined,
    explanation: data.explanation,
    evidence: mappedEvidence,
  };
}

/**
 * Submit text to POST /api/v1/analyze on the real backend.
 */
export async function analyzeClaim(
  text: string,
  options: AnalyzeOptions = {},
): Promise<VerificationResult> {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Enter a claim, article or message to verify.");
  }

  const payload = {
    text: trimmed,
    language: options.language || "auto",
  };

  const response = await apiFetch<BackendAnalysisResponse>("/api/v1/analyze", {
    method: "POST",
    body: payload,
    signal: options.signal,
    timeoutMs: options.timeoutMs ?? 15000,
  });

  return mapBackendResponseToVerificationResult(response);
}

/**
 * Retrieve a previously completed analysis by ID from GET /api/v1/analysis/{id}.
 */
export async function getAnalysisById(
  analysisId: string,
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<VerificationResult> {
  const response = await apiFetch<BackendAnalysisResponse>(
    `/api/v1/analysis/${encodeURIComponent(analysisId)}`,
    {
      method: "GET",
      signal: options.signal,
      timeoutMs: options.timeoutMs ?? 10000,
    },
  );

  return mapBackendResponseToVerificationResult(response);
}

export interface BackendAnalysisSummary {
  analysis_id: string;
  language: string;
  claim: string;
  claim_type?: string | null;
  assessment: VerificationResult["assessment"];
  confidence?: number | null;
  confidence_tier?: string | null;
  evidence_strength?: VerificationResult["evidenceStrength"] | null;
  evidence_count: number;
  created_at?: string | null;
}

/**
 * Fetch a list of previously completed analyses from GET /api/v1/analyses.
 */
export async function listAnalyses(
  options: { limit?: number; offset?: number; signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<import("../../types").AnalysisSummary[]> {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.offset) params.set("offset", String(options.offset));
  const query = params.toString() ? `?${params.toString()}` : "";

  const response = await apiFetch<BackendAnalysisSummary[]>(`/api/v1/analyses${query}`, {
    method: "GET",
    signal: options.signal,
    timeoutMs: options.timeoutMs ?? 10000,
  });

  return response.map((item) => ({
    analysisId: item.analysis_id,
    language: (["en", "hi", "te"].includes(item.language) ? item.language : "en") as Language,
    claim: item.claim,
    claimType: item.claim_type || "Factual claim",
    assessment: item.assessment,
    confidence: item.confidence ?? null,
    confidenceTier: item.confidence_tier || undefined,
    evidenceStrength: item.evidence_strength || undefined,
    evidenceCount: item.evidence_count,
    createdAt: item.created_at || undefined,
  }));
}
