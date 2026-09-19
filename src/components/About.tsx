import { IconShield, IconAlert, IconCheck } from "./Icons";

export function About() {
  return (
    <div className="about-view fade-in">
      <header className="about-header">
        <span className="editorial-section-tag">PROJECT IDENTITY &amp; PURPOSE</span>
        <h1 className="about-title">WHY VERITRACE EXISTS</h1>
        <p className="about-subtitle">
          Detect the claim. Trace the evidence. An AI-assisted investigation studio built for transparency, multilingual accountability, and honest uncertainty.
        </p>
      </header>

      {/* Permanent Trust Principle Banner */}
      <div className="card responsible-ai-hero-box">
        <div className="trust-head">
          <IconShield className="trust-shield-icon" />
          <div>
            <span className="trust-tag">PERMANENT TRUST PRINCIPLE</span>
            <h2>Assessment, not absolute truth.</h2>
          </div>
        </div>
        <p className="trust-body">
          No automated artificial intelligence system can or should claim absolute factual infallibility.
          VeriTrace AI provides <strong>evidence-grounded assessments</strong>, not authoritative final judgments.
          We present the extracted claim, retrieve verifiable public sources, measure model confidence, and show the exact evidence trail so human researchers, journalists, and citizens can inspect and judge for themselves.
        </p>
      </div>

      <div className="about-sections-grid">
        {/* 1. Problem */}
        <section className="card about-section-card">
          <span className="section-step-label">01 / THE PROBLEM</span>
          <h3>Misinformation &amp; The Verification Gap</h3>
          <p>
            In modern media ecosystems, rumors spread instantaneously across encrypted chat groups and social networks. Existing fact-checking efforts produce rigorous debunks, but they are published hours or days later on separate websites. Readers rarely see them.
          </p>
          <p>
            Meanwhile, automated classification tools often assign a bare &quot;Fake&quot; label without providing evidence, demanding blind trust from users.
          </p>
        </section>

        {/* 2. Approach */}
        <section className="card about-section-card">
          <span className="section-step-label">02 / OUR APPROACH</span>
          <h3>Auditable Evidence Trails</h3>
          <p>
            VeriTrace inverts the traditional paradigm. Instead of asking you to trust an opaque score, VeriTrace identifies the exact factual proposition, queries trusted fact-checking registries and official sources, and evaluates whether those sources corroborate or contradict the claim.
          </p>
          <p>
            Every assessment is paired with direct hyperlinks, publication timestamps, and verbatim snippets.
          </p>
        </section>

        {/* 3. Multilingual NLP */}
        <section className="card about-section-card">
          <span className="section-step-label">03 / MULTILINGUAL FOCUS</span>
          <h3>English, Hindi, and Telugu</h3>
          <p>
            Misinformation in India is deeply multilingual. A viral claim originating in English is rapidly translated into regional languages with subtle semantic shifts.
          </p>
          <p>
            VeriTrace focuses specifically on English (`en`), Hindi (`hi`), and Telugu (`te`). We do not claim universal language coverage without proven linguistic models and verified data pipelines.
          </p>
        </section>

        {/* 4. Uncertainty */}
        <section className="card about-section-card">
          <span className="section-step-label">04 / UNCERTAINTY IS AN OUTCOME</span>
          <h3>Insufficient Evidence Is Valid</h3>
          <p>
            Most classifiers are forced to pick a side. In the real world, many claims simply cannot be proven true or false from available public records.
          </p>
          <p>
            VeriTrace treats &quot;Insufficient Evidence&quot; and &quot;Conflicting Evidence&quot; as first-class outcomes, preventing dangerous false certainty on breaking or ambiguous events.
          </p>
        </section>

        {/* 5. Scope & Limitations */}
        <section className="card about-section-card full-width">
          <span className="section-step-label">05 / KNOWN LIMITATIONS</span>
          <h3>Where VeriTrace Stands Today</h3>
          <div className="limitations-grid">
            <div className="limit-item">
              <IconAlert className="limit-icon" />
              <div>
                <strong>Evidence Coverage Limits</strong>
                <p>
                  Retrieval relies on indexed Google Fact Check tools and configured public repositories. Unrecorded local events or hyper-niche rumors without existing reporting may yield insufficient evidence.
                </p>
              </div>
            </div>

            <div className="limit-item">
              <IconAlert className="limit-icon" />
              <div>
                <strong>Temporal Shifts</strong>
                <p>
                  Claims regarding fluid developing situations (e.g. disaster counts, active legal proceedings) may reflect outdated reports if new developments have not yet been indexed.
                </p>
              </div>
            </div>

            <div className="limit-item">
              <IconAlert className="limit-icon" />
              <div>
                <strong>Human Judgment Is Vital</strong>
                <p>
                  VeriTrace is designed as an investigative assistant for journalists, researchers, and citizens — never as an automated censorship mechanism or replacement for critical thinking.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
