import { useState, useMemo, type CSSProperties } from "react";
import {
  IconChart,
  IconBulb,
  IconDoc,
  IconExternal,
  IconGlobe,
  IconHome,
  IconInfo,
  IconLayers,
  IconStrength,
  IconAlert,
  IconShield,
  IconArrow,
} from "./Icons";
import { ASSESSMENT_META, RELATION_META, percent } from "../presentation";
import { LANGUAGE_LABELS, type EvidenceItem, type VerificationResult } from "../types";

const TIMESTAMP: Intl.DateTimeFormatOptions = {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
};

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

/**
 * Claim Span Highlighting Component
 * Highlights relevant keywords or numbers in the extracted claim.
 */
function HighlightedClaim({ claim }: { claim: string }) {
  // Highlight numerical entities, currencies, or quoted key phrases
  const parts = useMemo(() => {
    const regex = /(\b(?:\d+(?:\.\d+)?%?|\d+\s*(?:percent|cr|lakh|crore|billion|million|rupees|rs\.?))\b|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/gi;
    const tokens: Array<{ text: string; highlight: boolean }> = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(claim)) !== null) {
      if (match.index > lastIndex) {
        tokens.push({ text: claim.substring(lastIndex, match.index), highlight: false });
      }
      tokens.push({ text: match[0], highlight: true });
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < claim.length) {
      tokens.push({ text: claim.substring(lastIndex), highlight: false });
    }

    return tokens.length > 0 ? tokens : [{ text: claim, highlight: false }];
  }, [claim]);

  return (
    <blockquote className="claim-quote">
      <span className="quote-mark">&ldquo;</span>
      {parts.map((p, i) =>
        p.highlight ? (
          <mark key={i} className="claim-span-highlight">
            {p.text}
          </mark>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
      <span className="quote-mark">&rdquo;</span>
    </blockquote>
  );
}

/**
 * Interactive Evidence Relationship Diagram (Lightweight SVG)
 */
function EvidenceRelationshipMap({
  claim,
  evidence,
}: {
  claim: string;
  evidence: EvidenceItem[];
}) {
  const [selectedId, setSelectedId] = useState<string | null>(
    evidence.length > 0 ? evidence[0].id : null,
  );

  const selectedItem = evidence.find((e) => e.id === selectedId) || evidence[0];

  if (evidence.length === 0) {
    return (
      <div className="empty-relationship-box">
        <span className="empty-tag">NO CONNECTED EVIDENCE</span>
        <p>No external citations were linked to this claim proposition.</p>
      </div>
    );
  }

  return (
    <div className="evidence-relationship-map">
      <div className="map-tree">
        {/* Central Claim Root */}
        <div className="tree-root">
          <div className="tree-root-badge">CENTRAL CLAIM</div>
          <div className="tree-root-text">
            {claim.length > 90 ? claim.slice(0, 88) + "…" : claim}
          </div>
        </div>

        {/* Tree Branches */}
        <div className="tree-branches">
          {evidence.map((item, idx) => {
            const relMeta = RELATION_META[item.relation] || RELATION_META.INSUFFICIENT;
            const isSelected = selectedItem?.id === item.id;

            return (
              <div
                key={item.id}
                className={`tree-branch-node ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedId(item.id)}
                role="button"
                tabIndex={0}
              >
                <div className="branch-line" />
                <div className="branch-card">
                  <div className="branch-header">
                    <span
                      className="branch-rel-tag"
                      style={{ color: relMeta.color, backgroundColor: relMeta.soft }}
                    >
                      {relMeta.label.toUpperCase()}
                    </span>
                    <span className="branch-src">{item.publisher || item.source}</span>
                  </div>
                  <div className="branch-title">{item.title}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Branch Inspection Panel */}
      {selectedItem && (
        <div className="map-selected-detail">
          <div className="detail-meta-row">
            <span className="detail-publisher">{selectedItem.publisher || selectedItem.source}</span>
            {selectedItem.publishedAt && (
              <span className="detail-date">{formatDate(selectedItem.publishedAt)}</span>
            )}
            <a
              href={selectedItem.url}
              target="_blank"
              rel="noreferrer"
              className="detail-link"
            >
              Open Citation →
            </a>
          </div>
          <p className="detail-snippet">&ldquo;{selectedItem.snippet}&rdquo;</p>
        </div>
      )}
    </div>
  );
}

/**
 * Chronological Evidence Timeline (when dates exist)
 */
function EvidenceTimeline({ items }: { items: EvidenceItem[] }) {
  const datedItems = useMemo(() => {
    return items
      .filter((i) => Boolean(i.publishedAt))
      .sort((a, b) => new Date(b.publishedAt!).getTime() - new Date(a.publishedAt!).getTime());
  }, [items]);

  if (datedItems.length === 0) return null;

  return (
    <div className="evidence-timeline-section">
      <h3 className="section-sub-heading">
        <span className="tag-pill">CHRONOLOGY</span>
        Evidence Timeline
      </h3>
      <div className="timeline-trail">
        {datedItems.map((item, idx) => (
          <div key={item.id} className="timeline-entry">
            <div className="timeline-marker" />
            <div className="timeline-content">
              <div className="timeline-time">{formatDate(item.publishedAt)}</div>
              <div className="timeline-title">{item.title}</div>
              <div className="timeline-src">{item.publisher || item.source}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const meta = RELATION_META[item.relation] || RELATION_META.INSUFFICIENT;
  const style = { "--rel-color": meta.color, "--rel-soft": meta.soft } as CSSProperties;

  return (
    <li className="evidence-card" style={style}>
      <div className="evidence-top">
        <span className="tag">{meta.label}</span>
        <span className="evidence-source">{item.publisher || item.source}</span>
        {item.publishedAt && (
          <span className="evidence-date" title={item.publishedAt}>
            • {formatDate(item.publishedAt)}
          </span>
        )}
        <a
          className="evidence-open"
          href={item.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${item.publisher || item.source} in a new tab`}
        >
          <IconExternal />
        </a>
      </div>
      <h3 className="evidence-title">{item.title}</h3>
      <p className="evidence-snippet">{item.snippet}</p>
      <div className="evidence-foot">
        <span className="scores">
          Relevance <b>{percent(item.relevanceScore)}</b>
          <i>•</i>
          Source quality <b>{percent(item.sourceQuality)}</b>
        </span>
        <a href={item.url} target="_blank" rel="noreferrer" className="open-source-link">
          Open source →
        </a>
      </div>
    </li>
  );
}

function CardHead({
  icon: Icon,
  title,
  note,
}: {
  icon: typeof IconDoc;
  title: string;
  note?: string;
}) {
  return (
    <div className="card-head">
      <span className="card-ico">
        <Icon />
      </span>
      <h2>
        {title}
        {note && <small> {note}</small>}
      </h2>
    </div>
  );
}

const BREAKDOWN_LABELS: Array<[string, string]> = [
  ["evidenceAgreement", "Evidence Agreement"],
  ["evidenceRelevance", "Evidence Relevance"],
  ["sourceQuality", "Source Quality"],
  ["modelConfidence", "Model Confidence"],
];

interface ResultProps {
  result: VerificationResult;
  onReset?: () => void;
}

export function Result({ result, onReset }: ResultProps) {
  const [copied, setCopied] = useState(false);
  const meta = ASSESSMENT_META[result.assessment] || ASSESSMENT_META.INSUFFICIENT_EVIDENCE;
  const VerdictIcon = meta.icon;
  const style = { "--verdict-color": meta.color, "--verdict-soft": meta.soft } as CSSProperties;

  const analysedOn = useMemo(
    () => new Date().toLocaleString(undefined, TIMESTAMP),
    [result],
  );

  const handleCopy = async () => {
    const lines = [
      `VeriTrace AI — Verification Assessment`,
      `Claim: "${result.claim}"`,
      `Language: ${LANGUAGE_LABELS[result.language] || result.language}`,
      `Assessment: ${meta.label}`,
      `Model Confidence: ${
        result.confidence !== null && result.confidence !== undefined
          ? percent(result.confidence)
          : "Uncalibrated Baseline"
      } (${result.confidenceTier || "Standard"})`,
      `Evidence Strength: ${result.evidenceStrength || "Not assessed"}`,
      ``,
      `Explanation:`,
      result.explanation,
      result.confidenceExplanation
        ? `\nUncertainty Notice:\n${result.confidenceExplanation}`
        : ``,
      ``,
      `Evidence Trail (${result.evidence.length} sources):`,
      ...(result.evidence.length > 0
        ? result.evidence.map(
            (e, i) =>
              `${i + 1}. [${RELATION_META[e.relation]?.label || e.relation}] ${e.title} — ${
                e.publisher || e.source
              } (${e.url})`,
          )
        : ["No external sources traced."]),
      ``,
      `AI-assisted assessment — review the cited sources. Model confidence reflects prediction strength; it does not guarantee factual truth.`,
    ]
      .filter((l) => l !== undefined)
      .join("\n");

    try {
      await navigator.clipboard.writeText(lines);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = lines;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const hasConfidence = result.confidence !== null && result.confidence !== undefined;

  // Specific special states
  const isInsufficient = result.assessment === "INSUFFICIENT_EVIDENCE";
  const isConflicting = result.assessment === "CONFLICTING_EVIDENCE";
  const isLowConfidence =
    result.confidenceTier?.includes("LOW") ||
    (hasConfidence && (result.confidence as number) < 0.5);

  return (
    <div className="result fade-in" style={style}>
      {/* Breadcrumb Navigation */}
      <div className="crumb">
        <IconHome />
        <span>Verification Result</span>
        <span className="crumb-sep">/</span>
        <span className="crumb-id">{result.analysisId ? `ID: ${result.analysisId}` : "Live Investigation"}</span>
      </div>

      {/* Primary Editorial Verdict Banner */}
      <header className="verdict-head">
        <div className="verdict-lead">
          <span className="verdict-ico">
            <VerdictIcon />
          </span>
          <div>
            <div className="verdict-eyebrow">FINAL VERIFICATION ASSESSMENT</div>
            <h1 className="verdict-name">
              <span>{meta.lead}</span>
              {meta.rest}
            </h1>
            <p className="verdict-summary">{meta.summary}</p>
            <p className="ai-disclaimer">
              <IconShield className="disclaimer-ico" />
              <span>
                Assessment, not absolute truth. Confidence reflects model prediction strength; it does not guarantee factual certainty.
              </span>
            </p>
          </div>
        </div>

        {/* Vital Metrics Grid */}
        <div className="stats">
          <div className="stat stat-confidence">
            <div className="stat-label">Model Confidence</div>
            <div className="stat-value">
              {hasConfidence ? percent(result.confidence) : "Baseline"}
            </div>
            {result.confidenceTier && (
              <div className="confidence-tier-pill" title="Calibrated Confidence Tier">
                {result.confidenceTier}
              </div>
            )}
            <div className="meter">
              <span style={{ width: hasConfidence ? percent(result.confidence) : "0%" }} />
            </div>
            <span className="stat-caption">Calibrated Temperature Scaling</span>
          </div>

          {[
            [IconStrength, "Evidence Strength", result.evidenceStrength || "NONE"],
            [IconDoc, "Claim Type", result.claimType || "Factual claim"],
            [IconGlobe, "Language", LANGUAGE_LABELS[result.language] || result.language],
          ].map(([Icon, label, value]) => (
            <div className="stat" key={label as string}>
              <div className="stat-row">
                <span className="stat-ico">
                  <Icon />
                </span>
                <div className="stat-label">{label as string}</div>
              </div>
              <div className="stat-value stat-value-sm">{value as string}</div>
            </div>
          ))}
        </div>
      </header>

      {/* Special State Callouts */}
      {isInsufficient && (
        <div className="special-state-banner state-insufficient" role="status">
          <IconInfo className="state-icon" />
          <div className="state-text">
            <strong>Insufficient Evidence:</strong>
            <p>
              We could not retrieve enough verified independent evidence to establish a definitive assessment. In objective fact-checking, insufficient evidence is a legitimate outcome, not a failure.
            </p>
          </div>
        </div>
      )}

      {isConflicting && (
        <div className="special-state-banner state-conflicting" role="status">
          <IconAlert className="state-icon" />
          <div className="state-text">
            <strong>Conflicting Evidence Detected:</strong>
            <p>
              Available reputable sources genuinely disagree. Review both supporting and contradicting citations below before drawing conclusions.
            </p>
          </div>
        </div>
      )}

      {isLowConfidence && !isInsufficient && (
        <div className="special-state-banner state-low-confidence" role="status">
          <IconAlert className="state-icon" />
          <div className="state-text">
            <strong>Low Confidence Signal:</strong>
            <p>
              The model signal has high uncertainty. We strongly recommend manual review of the cited source citations.
            </p>
          </div>
        </div>
      )}

      {/* Action Toolbar */}
      <div className="result-toolbar">
        {onReset && (
          <button
            className="btn-editorial-primary"
            onClick={onReset}
            aria-label="Run another analysis"
          >
            <span>Run another analysis</span>
            <IconArrow className="arrow-sm" />
          </button>
        )}
        <button
          className="btn-editorial-secondary"
          onClick={handleCopy}
          aria-label="Copy result summary to clipboard"
        >
          {copied ? "Copied to Clipboard!" : "Copy Investigation"}
        </button>
      </div>

      {/* Columns Layout */}
      <div className="result-cols">
        {/* Left Column: Claim, Reasoning, Calibration */}
        <div className="result-col">
          {/* Claim Card with Span Highlighting */}
          <section className="card">
            <CardHead icon={IconDoc} title="Extracted Claim" />
            <HighlightedClaim claim={result.claim} />
            <dl className="meta-row">
              {[
                ["Language", LANGUAGE_LABELS[result.language] || result.language],
                ["Claim Type", result.claimType || "Factual claim"],
                ["Sources Traced", String(result.evidence.length)],
                ["Analyzed On", analysedOn],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* Evidence Relationship Tree */}
          <section className="card">
            <CardHead icon={IconLayers} title="Evidence Relationship Map" note="(Claim to Sources)" />
            <EvidenceRelationshipMap claim={result.claim} evidence={result.evidence} />
          </section>

          {/* Reasoning & Decision Fusion */}
          <section className="card">
            <CardHead icon={IconBulb} title="Reasoning & Decision Trace" />
            <p className="card-body">{result.explanation}</p>

            {result.confidenceExplanation && (
              <div className="callout callout-warning">
                <IconAlert />
                <div>
                  <strong>Uncertainty &amp; Evidence Note:</strong>
                  <p style={{ margin: "4px 0 0 0" }}>{result.confidenceExplanation}</p>
                </div>
              </div>
            )}

            <p className="callout">
              <IconInfo />
              <span>
                Assessment, not absolute truth. Real verification requires independent corroboration from verifiable external sources.
              </span>
            </p>
          </section>

          {/* Confidence & Calibration Details */}
          <section className="card">
            <CardHead icon={IconChart} title="Confidence & Calibration" />
            {result.confidenceBreakdown ? (
              <div className="breakdown">
                {BREAKDOWN_LABELS.map(([key, label]) => {
                  const val = (result.confidenceBreakdown as Record<string, number | undefined>)?.[key];
                  if (val === undefined || val === null) return null;
                  return (
                    <div className="breakdown-row" key={key}>
                      <span className="breakdown-name">{label}</span>
                      <div className="meter">
                        <span style={{ width: percent(val) }} />
                      </div>
                      <span className="val">{percent(val)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="card-body">
                Certainty tier: <strong>{result.confidenceTier || "Standard"}</strong>.
                Granular sub-scores are calculated by the decision engine when fine-tuned ML models run.
              </p>
            )}
            <p className="hint card-note">
              Measured backend values calibrated using post-hoc temperature scaling and uncertainty-aware decision fusion.
            </p>
          </section>
        </div>

        {/* Right Column: Evidence Trail & Timeline */}
        <aside className="result-col">
          <section className="card card-trail">
            <CardHead
              icon={IconLayers}
              title="Evidence Trail"
              note={`(${result.evidence.length} ${
                result.evidence.length === 1 ? "source" : "sources"
              })`}
            />

            {result.evidence.length > 0 ? (
              <>
                <ul className="evidence-list">
                  {result.evidence.map((item) => (
                    <EvidenceCard key={item.id} item={item} />
                  ))}
                </ul>
                <EvidenceTimeline items={result.evidence} />
              </>
            ) : (
              <div className="empty-trail">
                <p className="card-body">
                  No verifiable external fact-checking sources were traced for this input.
                </p>
                <p className="card-note hint">
                  Without verifiable citations, VeriTrace restricts certainty to <strong>Insufficient Evidence</strong>.
                </p>
              </div>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
