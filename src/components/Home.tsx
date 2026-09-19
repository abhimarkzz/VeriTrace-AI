import { EvidenceNetwork } from "./EvidenceNetwork";
import { IconArrow, IconCheck, IconShield, IconGlobe } from "./Icons";
import { BrandMark } from "./Navigation";
import { type Language } from "../types";

interface HomeProps {
  onAnalyzeClaim: (presetClaim?: string, lang?: Language) => void;
  onExploreEvidence: () => void;
}

export function Home({ onAnalyzeClaim, onExploreEvidence }: HomeProps) {
  const verifiedSamples = [
    {
      lang: "en" as Language,
      langLabel: "English",
      code: "EN",
      claim: "Reserve Bank of India maintained policy repo rate at 6.5 percent.",
      category: "Macroeconomic Policy",
      checkStatus: "Verifiable official record",
    },
    {
      lang: "hi" as Language,
      langLabel: "Hindi",
      code: "HI",
      claim: "सरकार ने 500 रुपये के सभी पुराने नोट तुरंत बंद करने का आदेश दिया।",
      category: "Viral Social Forward",
      checkStatus: "Known rumor debunked by official PIB fact check",
    },
    {
      lang: "te" as Language,
      langLabel: "Telugu",
      code: "TE",
      claim: "భారతదేశంలో డిజిటల్ చెల్లింపులు యూపీఐ సేవలు పూర్తిగా రద్దు చేయబడ్డాయి.",
      category: "Regional Messaging",
      checkStatus: "Fact-checked financial policy claim",
    },
  ];

  return (
    <div className="home-view fade-in">
      {/* ── 1. Hero Section ────────────────────────────────────────── */}
      <section className="editorial-hero">
        <div className="container hero-container">
          <div className="hero-content">
            <div className="eyebrow-wrapper">
              <BrandMark size={20} />
              <span className="eyebrow-pill">MULTILINGUAL EVIDENCE INTELLIGENCE</span>
              <span className="lang-scope-badge">English · Hindi · Telugu</span>
            </div>

            <h1 className="hero-headline">
              VERIFY WHAT <br />
              <span className="hero-accent-word">YOU READ.</span>
            </h1>

            <p className="hero-lede">
              Analyze claims, trace evidence, compare sources, and understand what the available
              evidence actually supports. We replace ungrounded verdicts with transparent,
              auditable evidence trails.
            </p>

            <div className="hero-actions">
              <button
                className="btn-editorial-primary"
                onClick={() => onAnalyzeClaim()}
                aria-label="Begin Your Verification"
              >
                <span>Analyze a Claim</span>
                <IconArrow className="arrow" />
              </button>

              <button
                className="btn-editorial-secondary"
                onClick={onExploreEvidence}
              >
                <span>Explore Evidence</span>
              </button>
            </div>

            <div className="hero-micro-copy">
              <IconShield className="micro-icon" />
              <span>Evidence-grounded multilingual verification · No opaque black-box verdicts</span>
            </div>
          </div>

          <div className="hero-visual">
            <EvidenceNetwork
              claimText="Reserve Bank of India maintained policy repo rate at 6.5 percent."
              onSelectNode={(node) => {
                if (node.type === "claim") {
                  onAnalyzeClaim(node.details);
                }
              }}
            />
          </div>
        </div>
      </section>

      {/* ── 2. The Verification Gap ────────────────────────────────── */}
      <section className="section-gap">
        <div className="container">
          <div className="section-header-editorial">
            <span className="editorial-section-tag">01 / THE VERIFICATION GAP</span>
            <h2 className="editorial-title">
              THE CLAIM ARRIVES FIRST. <br />
              <span className="editorial-title-faint">THE EVIDENCE COMES LATER.</span>
            </h2>
            <p className="editorial-subtitle">
              Misinformation exploits the friction of manual verification. When sensational claims spread across chat apps and social feeds, users react before evidence can be cross-checked.
            </p>
          </div>

          <div className="gap-flows-grid">
            {/* Unchecked Flow */}
            <div className="flow-card flow-unchecked">
              <div className="flow-card-head">
                <span className="flow-badge warning">UNCHECKED SPREAD</span>
                <h3>How Misinformation Spreads</h3>
              </div>
              <div className="flow-pipeline">
                <div className="flow-node">
                  <span className="node-step">01</span>
                  <strong>MESSAGE</strong>
                  <span className="node-caption">Sensational claim posted</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node">
                  <span className="node-step">02</span>
                  <strong>SHARE</strong>
                  <span className="node-caption">Viral forwards in groups</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node">
                  <span className="node-step">03</span>
                  <strong>REACT</strong>
                  <span className="node-caption">Outrage or emotional belief</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node danger">
                  <span className="node-step">04</span>
                  <strong>CONFUSION</strong>
                  <span className="node-caption">Ungrounded public narrative</span>
                </div>
              </div>
            </div>

            {/* VeriTrace Flow */}
            <div className="flow-card flow-veritrace">
              <div className="flow-card-head">
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <BrandMark size={20} />
                  <span className="flow-badge verified">VERITRACE PIPELINE</span>
                </div>
                <h3>Evidence-Grounded Resolution</h3>
              </div>
              <div className="flow-pipeline">
                <div className="flow-node">
                  <span className="node-step">01</span>
                  <strong>CLAIM</strong>
                  <span className="node-caption">Extracted factual statement</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node">
                  <span className="node-step">02</span>
                  <strong>EVIDENCE</strong>
                  <span className="node-caption">Independent sources retrieved</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node">
                  <span className="node-step">03</span>
                  <strong>CROSS-CHECK</strong>
                  <span className="node-caption">NLI support / contradiction</span>
                </div>
                <div className="flow-arrow">→</div>
                <div className="flow-node success">
                  <span className="node-step">04</span>
                  <strong>ASSESSMENT</strong>
                  <span className="node-caption">Transparent audit trail</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. From Verdict to Evidence Trail (Before / After) ─────── */}
      <section className="section-contrast">
        <div className="container">
          <div className="section-header-editorial">
            <span className="editorial-section-tag">02 / PRODUCT PARADIGM</span>
            <h2 className="editorial-title">
              FROM A VERDICT <br />
              <span className="editorial-title-faint">TO AN EVIDENCE TRAIL.</span>
            </h2>
            <p className="editorial-subtitle">
              Most fact-checking tools offer only a binary label. VeriTrace provides the entire chain of reasoning.
            </p>
          </div>

          <div className="contrast-grid">
            <div className="contrast-card without-card">
              <div className="contrast-eyebrow">CONVENTIONAL SYSTEMS</div>
              <h3>Without VeriTrace</h3>
              <ul className="contrast-list">
                <li>
                  <span className="bullet-neg">✕</span>
                  <div>
                    <strong>Bare Label</strong>
                    <p>A single &quot;False&quot; or &quot;True&quot; verdict without transparent reasoning.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-neg">✕</span>
                  <div>
                    <strong>No Reasoning Trace</strong>
                    <p>Users cannot verify why the model flagged the text.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-neg">✕</span>
                  <div>
                    <strong>Manual Source Hunting</strong>
                    <p>The reader must independently search the web to corroborate findings.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-neg">✕</span>
                  <div>
                    <strong>Forced Certainty</strong>
                    <p>Nuanced or inconclusive claims are forced into arbitrary binary bins.</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="contrast-card with-card">
              <div className="contrast-eyebrow highlight">VERITRACE AI</div>
              <h3>With VeriTrace</h3>
              <ul className="contrast-list">
                <li>
                  <span className="bullet-pos">✓</span>
                  <div>
                    <strong>Extracted Checkable Claim</strong>
                    <p>Isolates the factual core from noise, opinions, and questions.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-pos">✓</span>
                  <div>
                    <strong>Traced Source Citations</strong>
                    <p>Links directly to reputable news organizations and official gazettes.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-pos">✓</span>
                  <div>
                    <strong>Explicit Support &amp; Contradiction</strong>
                    <p>Shows which quotes corroborate and which debunk the claim.</p>
                  </div>
                </li>
                <li>
                  <span className="bullet-pos">✓</span>
                  <div>
                    <strong>Calibrated Uncertainty</strong>
                    <p>Model confidence is distinguished from truth probability.</p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. How VeriTrace Works (01 - 07 Numbered Process) ──────── */}
      <section className="section-process">
        <div className="container">
          <div className="section-header-editorial">
            <span className="editorial-section-tag">03 / ARCHITECTURE IN ACTION</span>
            <h2 className="editorial-title">
              HOW VERITRACE <br />
              <span className="editorial-title-faint">INVESTIGATES A CLAIM.</span>
            </h2>
            <p className="editorial-subtitle">
              Seven decoupled stages ensure separation of evidence retrieval from verdict synthesis.
            </p>
          </div>

          <div className="process-timeline">
            {[
              {
                num: "01",
                title: "INGEST",
                desc: "Receive raw text from news articles, social-media posts, or forwarded chat messages.",
              },
              {
                num: "02",
                title: "UNDERSTAND",
                desc: "Detect language (English, Hindi, Telugu) and extract checkable factual assertions.",
              },
              {
                num: "03",
                title: "ANALYZE",
                desc: "Run multilingual representations to evaluate linguistic structure and claim patterns.",
              },
              {
                num: "04",
                title: "RETRIEVE",
                desc: "Fetch external fact checks, reporting, and reference materials matching the exact claim.",
              },
              {
                num: "05",
                title: "COMPARE",
                desc: "Determine whether each retrieved source supports, contradicts, or provides context.",
              },
              {
                num: "06",
                title: "ASSESS",
                desc: "Synthesize classifier predictions with evidence agreement via uncertainty-aware fusion.",
              },
              {
                num: "07",
                title: "EXPLAIN",
                desc: "Present full citations, source snippets, calibrated confidence, and transparent limits.",
              },
            ].map((step) => (
              <div className="process-item" key={step.num}>
                <div className="process-number">{step.num}</div>
                <div className="process-body">
                  <h3 className="process-title">{step.title}</h3>
                  <p className="process-desc">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. Multilingual Section ────────────────────────────────── */}
      <section className="section-multilingual">
        <div className="container">
          <div className="section-header-editorial">
            <span className="editorial-section-tag">04 / LANGUAGE COVERAGE</span>
            <h2 className="editorial-title">
              ONE SYSTEM. <br />
              <span className="editorial-title-faint">MULTIPLE LANGUAGES.</span>
            </h2>
            <p className="editorial-subtitle">
              Misinformation in multilingual societies rarely stays in one language. VeriTrace provides focused NLP verification in English, Hindi, and Telugu.
            </p>
          </div>

          <div className="multilingual-grid">
            {verifiedSamples.map((sample) => (
              <div className="lang-sample-card" key={sample.lang}>
                <div className="card-top-row">
                  <span className="lang-badge-large">{sample.code}</span>
                  <div className="lang-meta-info">
                    <strong>{sample.langLabel}</strong>
                    <span>{sample.category}</span>
                  </div>
                </div>

                <blockquote className="sample-claim-text">
                  &ldquo;{sample.claim}&rdquo;
                </blockquote>

                <div className="sample-status-row">
                  <IconCheck className="status-ico" />
                  <span>{sample.checkStatus}</span>
                </div>

                <button
                  className="btn-card-action"
                  onClick={() => onAnalyzeClaim(sample.claim, sample.lang)}
                >
                  <span>Test This in Analyzer</span>
                  <IconArrow className="arrow-sm" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. Bottom CTA Section ──────────────────────────────────── */}
      <section className="section-cta-editorial">
        <div className="container">
          <div className="cta-box">
            <div className="cta-content">
              <span className="cta-eyebrow">READY TO INVESTIGATE</span>
              <h2>Start with any headline, tweet, or forwarded message.</h2>
              <p>
                Experience calibrated AI verification grounded in real citations across English, Hindi, and Telugu.
              </p>
            </div>
            <div className="cta-action">
              <button
                className="btn-editorial-primary btn-large"
                onClick={() => onAnalyzeClaim()}
              >
                <span>Open Analysis Workspace</span>
                <IconArrow className="arrow" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
