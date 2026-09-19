import { useEffect, useState } from "react";
import { IconHistory, IconArrow, IconShield, IconInfo } from "./Icons";
import { fetchHistory, fetchAnalysisById } from "../services/verificationService";
import { ASSESSMENT_META, percent } from "../presentation";
import { LANGUAGE_LABELS, type AnalysisSummary, type VerificationResult } from "../types";

interface IntelligenceProps {
  onSelectAnalysis: (result: VerificationResult) => void;
  onNavigateAnalyze: () => void;
}

export function Intelligence({ onSelectAnalysis, onNavigateAnalyze }: IntelligenceProps) {
  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLoadingId, setSelectedLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const records = await fetchHistory({ limit: 50 });
        if (active) {
          setHistory(records);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load investigation history from database.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    loadData();
    return () => {
      active = false;
    };
  }, []);

  const handleOpenRecord = async (analysisId: string) => {
    setSelectedLoadingId(analysisId);
    try {
      const fullResult = await fetchAnalysisById(analysisId);
      onSelectAnalysis(fullResult);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : `Failed to retrieve analysis '${analysisId}'.`,
      );
      setSelectedLoadingId(null);
    }
  };

  // Compute honest distributions based purely on real historical data
  const totalCount = history.length;
  const supportedCount = history.filter((h) => h.assessment === "SUPPORTED").length;
  const misleadingCount = history.filter((h) => h.assessment === "POTENTIALLY_MISLEADING").length;
  const insufficientCount = history.filter((h) => h.assessment === "INSUFFICIENT_EVIDENCE").length;
  const conflictingCount = history.filter((h) => h.assessment === "CONFLICTING_EVIDENCE").length;

  return (
    <div className="intelligence-view fade-in">
      <header className="intelligence-header">
        <span className="editorial-section-tag">AUDIT LOG &amp; SYSTEM INTELLIGENCE</span>
        <h1 className="intelligence-title">SYSTEM INTELLIGENCE</h1>
        <p className="intelligence-subtitle">
          Real PostgreSQL-backed records of completed verifications, evidence distributions, and linguistic coverage.
        </p>
      </header>

      {/* Real Aggregate Distribution (Only shown when real history exists) */}
      {totalCount > 0 && (
        <div className="intelligence-summary-cards">
          <div className="card summary-card">
            <span className="summary-label">TOTAL VERIFICATIONS</span>
            <div className="summary-value">{totalCount}</div>
            <span className="summary-sub">Persisted in database</span>
          </div>

          <div className="card summary-card">
            <span className="summary-label">SUPPORTED</span>
            <div className="summary-value text-support">{supportedCount}</div>
            <span className="summary-sub">Corroborated by sources</span>
          </div>

          <div className="card summary-card">
            <span className="summary-label">POTENTIALLY MISLEADING</span>
            <div className="summary-value text-contradict">{misleadingCount}</div>
            <span className="summary-sub">Contradicted by evidence</span>
          </div>

          <div className="card summary-card">
            <span className="summary-label">INSUFFICIENT EVIDENCE</span>
            <div className="summary-value text-muted">{insufficientCount + conflictingCount}</div>
            <span className="summary-sub">Inconclusive / Disputed</span>
          </div>
        </div>
      )}

      {/* Main History Table / Cards */}
      <section className="card history-card">
        <div className="history-card-header">
          <div className="history-title-wrap">
            <IconHistory className="history-icon" />
            <h2>Analysis History</h2>
          </div>
          <span className="history-count">
            {loading ? "Loading…" : `${totalCount} records`}
          </span>
        </div>

        {error && (
          <div className="history-error-banner" role="alert">
            <IconInfo />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="history-loading-state">
            <div className="pulse-indicator" />
            <p>Fetching investigation history from database…</p>
          </div>
        ) : totalCount > 0 ? (
          <div className="history-records-list">
            {history.map((record) => {
              const meta =
                ASSESSMENT_META[record.assessment] || ASSESSMENT_META.INSUFFICIENT_EVIDENCE;
              const isOpening = selectedLoadingId === record.analysisId;

              return (
                <div key={record.analysisId} className="history-row">
                  <div className="row-main">
                    <div className="row-top">
                      <span
                        className="badge-verdict-sm"
                        style={{ color: meta.color, backgroundColor: meta.soft }}
                      >
                        {meta.label}
                      </span>
                      <span className="badge-lang-sm">
                        {LANGUAGE_LABELS[record.language] || record.language.toUpperCase()}
                      </span>
                      {record.createdAt && (
                        <span className="row-date">
                          {new Date(record.createdAt).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </span>
                      )}
                    </div>

                    <h3 className="row-claim">&ldquo;{record.claim}&rdquo;</h3>

                    <div className="row-stats">
                      <span>
                        Confidence: <b>{percent(record.confidence)}</b>{" "}
                        <small>({record.confidenceTier || "Standard"})</small>
                      </span>
                      <i>•</i>
                      <span>
                        Evidence sources: <b>{record.evidenceCount}</b>
                      </span>
                      {record.claimType && (
                        <>
                          <i>•</i>
                          <span>Type: {record.claimType}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="row-action">
                    <button
                      className="btn-view-investigation"
                      onClick={() => handleOpenRecord(record.analysisId)}
                      disabled={isOpening}
                    >
                      <span>{isOpening ? "Loading…" : "View Investigation"}</span>
                      <IconArrow className="arrow-sm" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="history-empty-state">
            <IconShield className="empty-shield" />
            <h3>Your investigation history will appear here.</h3>
            <p>
              As claims are submitted and analyzed against PostgreSQL, full auditable records
              will populate this table.
            </p>
            <button
              className="btn-editorial-primary"
              onClick={onNavigateAnalyze}
              style={{ marginTop: 16 }}
            >
              <span>Verify Your First Claim</span>
              <IconArrow className="arrow-sm" />
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
