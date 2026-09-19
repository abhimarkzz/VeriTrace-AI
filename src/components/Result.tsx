import { useMemo, type CSSProperties } from "react";
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

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const meta = RELATION_META[item.relation];
  const style = { "--rel-color": meta.color, "--rel-soft": meta.soft } as CSSProperties;

  return (
    <li className="evidence-card" style={style}>
      <div className="evidence-top">
        <span className="tag">{meta.label}</span>
        <span className="evidence-source">{item.source}</span>
        <a
          className="evidence-open"
          href={item.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${item.source} in a new tab`}
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
        <a href={item.url} target="_blank" rel="noreferrer">
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

const BREAKDOWN_LABELS: Array<[keyof VerificationResult["confidenceBreakdown"], string]> = [
  ["evidenceAgreement", "Evidence agreement"],
  ["evidenceRelevance", "Evidence relevance"],
  ["sourceQuality", "Source quality"],
  ["modelConfidence", "Model confidence"],
];

export function Result({ result }: { result: VerificationResult }) {
  const meta = ASSESSMENT_META[result.assessment];
  const VerdictIcon = meta.icon;
  const style = { "--verdict-color": meta.color, "--verdict-soft": meta.soft } as CSSProperties;

  const analysedOn = useMemo(
    () => new Date().toLocaleString(undefined, TIMESTAMP),
    // A fresh timestamp per result, not per re-render.
    [result],
  );

  return (
    <div className="result fade-in" style={style}>
      <div className="crumb">
        <IconHome />
        Verification Result
      </div>

      <header className="verdict-head">
        <div className="verdict-lead">
          <span className="verdict-ico">
            <VerdictIcon />
          </span>
          <div>
            <h1 className="verdict-name">
              <span>{meta.lead}</span>
              {meta.rest}
            </h1>
            <p className="verdict-summary">{meta.summary}</p>
          </div>
        </div>

        <div className="stats">
          <div className="stat stat-confidence">
            <div className="stat-label">Confidence</div>
            <div className="stat-value">{percent(result.confidence)}</div>
            <div className="meter">
              <span style={{ width: percent(result.confidence) }} />
            </div>
          </div>
          {(
            [
              [IconStrength, "Evidence Strength", result.evidenceStrength],
              [IconDoc, "Claim Type", result.claimType],
              [IconGlobe, "Language", LANGUAGE_LABELS[result.language]],
            ] as const
          ).map(([Icon, label, value]) => (
            <div className="stat" key={label}>
              <div className="stat-row">
                <span className="stat-ico">
                  <Icon />
                </span>
                <div className="stat-label">{label}</div>
              </div>
              <div className="stat-value stat-value-sm">{value}</div>
            </div>
          ))}
        </div>
      </header>

      <div className="result-cols">
        <div className="result-col">
          <section className="card">
            <CardHead icon={IconDoc} title="Claim Identified" />
            <blockquote className="claim-quote">{result.claim}</blockquote>
            <dl className="meta-row">
              {(
                [
                  ["Language", LANGUAGE_LABELS[result.language]],
                  ["Claim Type", result.claimType],
                  ["Sources Traced", String(result.evidence.length)],
                  ["Analyzed On", analysedOn],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="card">
            <CardHead icon={IconBulb} title="Why this result?" />
            <p className="card-body">{result.explanation}</p>
            <p className="callout">
              <IconInfo />
              <span>
                This assessment is based on multiple sources saying the same thing. It does
                not include opinions or unverified social media posts.
              </span>
            </p>
          </section>

          <section className="card">
            <CardHead icon={IconChart} title="Confidence Breakdown" />
            <div className="breakdown">
              {BREAKDOWN_LABELS.map(([key, label]) => (
                <div className="breakdown-row" key={key}>
                  <span className="breakdown-name">{label}</span>
                  <div className="meter">
                    <span style={{ width: percent(result.confidenceBreakdown[key]) }} />
                  </div>
                  <span className="val">{percent(result.confidenceBreakdown[key])}</span>
                </div>
              ))}
            </div>
            <p className="hint card-note">
              Prototype confidence score. These weights are illustrative and have not been
              calibrated against a validation set.
            </p>
          </section>
        </div>

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
              <ul className="evidence-list">
                {result.evidence.map((item) => (
                  <EvidenceCard key={item.id} item={item} />
                ))}
              </ul>
            ) : (
              <p className="card-body">
                No sources could be traced for this input, so there is no evidence trail to
                show.
              </p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
