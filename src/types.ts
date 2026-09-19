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
  publisher?: string;
  url: string;
  snippet: string;
  relevanceScore: number;
  sourceQuality: number;
  relation: Relation;
  publishedAt?: string;
}

export interface ConfidenceBreakdown {
  evidenceAgreement?: number;
  evidenceRelevance?: number;
  sourceQuality?: number;
  modelConfidence?: number;
  probabilities?: Record<string, number>;
}

export interface VerificationResult {
  analysisId?: string;
  claim: string;
  language: Language;
  claimType: string;
  assessment: Assessment;
  confidence: number | null;
  confidenceTier?: string;
  confidenceExplanation?: string;
  confidenceBreakdown?: ConfidenceBreakdown;
  evidenceStrength?: EvidenceStrength;
  explanation: string;
  evidence: EvidenceItem[];
}

export interface AnalysisSummary {
  analysisId: string;
  language: Language;
  claim: string;
  claimType?: string;
  assessment: Assessment;
  confidence: number | null;
  confidenceTier?: string;
  evidenceStrength?: EvidenceStrength;
  evidenceCount: number;
  createdAt?: string;
}

export const STAGES = [
  "Receiving input",
  "Detecting language",
  "Extracting claims",
  "Running multilingual model",
  "Retrieving evidence",
  "Ranking evidence",
  "Verifying evidence",
  "Computing confidence",
  "Preparing explanation",
] as const;

export type Stage = (typeof STAGES)[number];

export type StageStatus = "pending" | "active" | "complete";

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "English",
  hi: "Hindi",
  te: "Telugu",
};
