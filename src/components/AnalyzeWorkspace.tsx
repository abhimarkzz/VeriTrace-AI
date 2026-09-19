import { useState } from "react";
import { IconArrow, IconAlert, IconGlobe } from "./Icons";
import { DEMO_PROMPTS } from "../mock/demoClaims";
import { LANGUAGE_LABELS, type Language } from "../types";

export type AnalysisMode = "claim" | "article" | "social" | "forward";

interface AnalyzeWorkspaceProps {
  initialText?: string;
  initialLanguage?: string;
  onVerify: (text: string, language: string) => Promise<void>;
  isLoading: boolean;
  currentStageIndex: number;
  error: string | null;
  onClearError: () => void;
}

const MODES: Array<{ id: AnalysisMode; label: string; placeholder: string; hint: string }> = [
  {
    id: "claim",
    label: "FACTUAL CLAIM",
    placeholder: "Paste a single factual statement (e.g., 'Reserve Bank maintained repo rate at 6.5 percent')…",
    hint: "Optimal for statistical statements, policy quotes, or breaking claims.",
  },
  {
    id: "article",
    label: "NEWS ARTICLE",
    placeholder: "Paste news headline and article paragraphs for claim extraction and cross-check…",
    hint: "Extracts checkable claims from surrounding journalistic context.",
  },
  {
    id: "social",
    label: "SOCIAL POST",
    placeholder: "Paste post text, viral thread excerpt, or social statement…",
    hint: "Filters conversational filler to isolate the core assertion.",
  },
  {
    id: "forward",
    label: "FORWARDED MESSAGE",
    placeholder: "Paste viral forwarded message from messaging platforms…",
    hint: "Identifies recurring rumors and verifies against official fact checks.",
  },
];

const PIPELINE_STAGES = [
  { step: "01", name: "Receiving & Normalizing", desc: "Sanitizing input and handling character encodings" },
  { step: "02", name: "Language Detection", desc: "Verifying English, Hindi, or Telugu language models" },
  { step: "03", name: "Claim Extraction", desc: "Isolating factual, checkable propositions" },
  { step: "04", name: "Evidence Retrieval", desc: "Searching official registries and verified fact-check datasets" },
  { step: "05", name: "Ranking & NLI Verification", desc: "Evaluating entailment, contradiction, and neutral sources" },
  { step: "06", name: "Uncertainty Calibration", desc: "Applying post-hoc temperature scaling and fusion rules" },
  { step: "07", name: "Assessment Synthesis", desc: "Synthesizing evidence trail and transparent explanations" },
];

export function AnalyzeWorkspace({
  initialText = "",
  initialLanguage = "auto",
  onVerify,
  isLoading,
  currentStageIndex,
  error,
  onClearError,
}: AnalyzeWorkspaceProps) {
  const [text, setText] = useState(initialText);
  const [selectedLanguage, setSelectedLanguage] = useState(initialLanguage);
  const [activeMode, setActiveMode] = useState<AnalysisMode>("claim");

  const currentModeInfo = MODES.find((m) => m.id === activeMode) || MODES[0];

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onVerify(trimmed, selectedLanguage);
  };

  const handleClear = () => {
    setText("");
    onClearError();
  };

  const handleSelectSample = (sampleText: string, sampleLang: Language) => {
    setText(sampleText);
    setSelectedLanguage(sampleLang);
    onClearError();
  };

  return (
    <div className="workspace-container fade-in">
      <header className="workspace-header">
        <span className="editorial-section-tag">INVESTIGATION WORKSPACE</span>
        <h1 className="workspace-title">ANALYZE A CLAIM</h1>
        <p className="workspace-subtitle">
          Submit text in <strong>English</strong>, <strong>Hindi</strong>, or <strong>Telugu</strong>.
          VeriTrace isolates checkable claims, retrieves independent evidence, and computes an uncertainty-calibrated assessment.
        </p>
      </header>

      {/* Mode Selector Tabs */}
      <div className="mode-tabs" role="tablist" aria-label="Input Mode">
        {MODES.map((mode) => (
          <button
            key={mode.id}
            role="tab"
            aria-selected={activeMode === mode.id}
            className={`mode-tab ${activeMode === mode.id ? "active" : ""}`}
            onClick={() => setActiveMode(mode.id)}
          >
            {mode.label}
          </button>
        ))}
      </div>

      {/* Primary Input Card */}
      <div className="card workspace-card">
        <form onSubmit={handleSubmit}>
          <div className="textarea-wrapper">
            <textarea
              className="editorial-textarea"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (error) onClearError();
              }}
              placeholder="Paste a news article, social media post, or forwarded message…"
              rows={6}
              disabled={isLoading}
              aria-label="Text to verify"
            />
            <div className="textarea-meta">
              <span className="mode-hint">{currentModeInfo.hint}</span>
              <span className="char-counter">{text.length} characters</span>
            </div>
          </div>

          <div className="composer-action-bar">
            <div className="language-selector-group">
              <span className="lang-icon-wrap">
                <IconGlobe />
              </span>
              <select
                className="editorial-select"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                disabled={isLoading}
                aria-label="Language"
              >
                <option value="auto">Auto-detect language</option>
                {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>
                    {label} ({code})
                  </option>
                ))}
              </select>
              <span className="lang-support-note">EN · HI · TE</span>
            </div>

            <div className="actions-right">
              {text.length > 0 && !isLoading && (
                <button
                  type="button"
                  className="btn-text-clear"
                  onClick={handleClear}
                >
                  Clear
                </button>
              )}

              <button
                type="submit"
                className="btn-editorial-primary btn-submit-verify"
                disabled={text.trim().length === 0 || isLoading}
                aria-label="Verify claim"
              >
                <span>{isLoading ? "Analyzing..." : "Verify claim"}</span>
                <IconArrow className="arrow" />
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div className="workspace-error-banner" role="alert">
            <IconAlert className="error-icon" />
            <div className="error-text-wrap">
              <strong>Verification Request Notice:</strong>
              <p>{error}</p>
            </div>
            <button
              className="btn-retry-action"
              onClick={() => handleSubmit()}
              disabled={text.trim().length === 0 || isLoading}
              aria-label="Try again"
            >
              Try again
            </button>
          </div>
        )}
      </div>

      {/* Loading In-Flight Pipeline State */}
      {isLoading && (
        <div className="card pipeline-card fade-in" aria-live="polite">
          <div className="pipeline-header">
            <div className="pulse-indicator" />
            <h3>INVESTIGATING CLAIM IN REAL TIME</h3>
            <span className="pipeline-counter">
              STAGE {Math.min(currentStageIndex + 1, 7)} OF 07
            </span>
          </div>

          <div className="pipeline-stages-list">
            {PIPELINE_STAGES.map((stage, idx) => {
              const isPassed = idx < currentStageIndex;
              const isCurrent = idx === currentStageIndex;
              return (
                <div
                  key={stage.step}
                  className={`pipeline-stage-row ${
                    isPassed ? "completed" : isCurrent ? "current" : "pending"
                  }`}
                >
                  <span className="stage-step-num">{stage.step}</span>
                  <div className="stage-info">
                    <strong>{stage.name}</strong>
                    <span className="stage-sub">{stage.desc}</span>
                  </div>
                  <span className="stage-status-indicator">
                    {isPassed ? "Completed" : isCurrent ? "Processing…" : "Queued"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Verified Demo Prompts Chips */}
      {!isLoading && (
        <section className="verified-demos-section">
          <div className="demos-header">
            <span className="demos-label">TRY A VERIFIED FACT-CHECK PROMPT</span>
            <span className="demos-sub">Real claims with verifiable source citations</span>
          </div>

          <div className="demo-chips-grid">
            {DEMO_PROMPTS.map((demo) => (
              <button
                key={demo.id}
                type="button"
                className="editorial-demo-chip"
                aria-label={`Try sample claim: ${demo.label}`}
                onClick={() => handleSelectSample(demo.text, demo.language)}
              >
                <div className="chip-meta">
                  <span className="chip-lang-badge">{demo.language.toUpperCase()}</span>
                  <span className="chip-lang-name">{LANGUAGE_LABELS[demo.language]}</span>
                </div>
                <div className="chip-title">{demo.label}</div>
                <div className="chip-preview">{demo.text}</div>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
