import type { ComponentType, SVGProps } from "react";
import { IconAlert, IconCheck, IconQuestion, IconSplit } from "./components/Icons";
import type { Assessment, Relation } from "./types";

interface AssessmentMeta {
  /** Full label, used where the verdict appears inline. */
  label: string;
  /** The headline splits so the leading words can carry the verdict colour. */
  lead: string;
  rest: string;
  summary: string;
  color: string;
  soft: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}

export const ASSESSMENT_META: Record<Assessment, AssessmentMeta> = {
  SUPPORTED: {
    label: "Supported by evidence",
    lead: "Supported",
    rest: " by evidence",
    summary:
      "The available evidence supports the claim. Multiple reliable sources report the same information.",
    color: "var(--support)",
    soft: "var(--support-soft)",
    icon: IconCheck,
  },
  POTENTIALLY_MISLEADING: {
    label: "Potentially misleading",
    lead: "Potentially",
    rest: " misleading",
    summary:
      "The evidence contradicts the claim as stated. Reliable sources report something different.",
    color: "var(--contradict)",
    soft: "var(--contradict-soft)",
    icon: IconAlert,
  },
  CONFLICTING_EVIDENCE: {
    label: "Conflicting evidence",
    lead: "Conflicting",
    rest: " evidence",
    summary:
      "Reliable sources genuinely disagree on this claim, so it cannot be resolved in one direction.",
    color: "var(--neutral)",
    soft: "var(--neutral-soft)",
    icon: IconSplit,
  },
  INSUFFICIENT_EVIDENCE: {
    label: "Insufficient evidence",
    lead: "Insufficient",
    rest: " evidence",
    summary:
      "Not enough evidence was found to assess this claim either way. That is an outcome, not a failure.",
    color: "var(--text-muted)",
    soft: "var(--surface-sunken)",
    icon: IconQuestion,
  },
};

export const RELATION_META: Record<Relation, { label: string; color: string; soft: string }> = {
  SUPPORT: { label: "Supports", color: "var(--support)", soft: "var(--support-soft)" },
  CONTRADICT: { label: "Contradicts", color: "var(--contradict)", soft: "var(--contradict-soft)" },
  INSUFFICIENT: { label: "Not conclusive", color: "var(--neutral)", soft: "var(--neutral-soft)" },
};

export const percent = (value: number): string => `${Math.round(value * 100)}%`;
