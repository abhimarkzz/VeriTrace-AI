export type Language = "en" | "hi" | "te";

export type Relation = "SUPPORT" | "CONTRADICT" | "INSUFFICIENT";

export type Assessment =
  | "SUPPORTED"
  | "POTENTIALLY_MISLEADING"
  | "INSUFFICIENT_EVIDENCE"
  | "CONFLICTING_EVIDENCE";

export type EvidenceStrength = "WEAK" | "MODERATE" | "STRONG";

export interface EvidenceItem {
  id: string;
  title: string;
  source: string;
  url: string;
  snippet: string;
  relevanceScore: number;
  sourceQuality: number;
  relation: Relation;
}

export interface ConfidenceBreakdown {
  evidenceAgreement: number;
  evidenceRelevance: number;
  sourceQuality: number;
  modelConfidence: number;
}

export interface VerificationResult {
  claim: string;
  language: Language;
  claimType: string;
  assessment: Assessment;
  confidence: number;
  confidenceBreakdown: ConfidenceBreakdown;
  evidenceStrength: EvidenceStrength;
  explanation: string;
  evidence: EvidenceItem[];
}

export const STAGES = [
  "Detecting language",
  "Extracting claim",
  "Understanding claim",
  "Searching for evidence",
  "Comparing evidence",
  "Generating assessment",
] as const;

export type Stage = (typeof STAGES)[number];

export type StageStatus = "pending" | "active" | "complete";

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "English",
  hi: "Hindi",
  te: "Telugu",
};
