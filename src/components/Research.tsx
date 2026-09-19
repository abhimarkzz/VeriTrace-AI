import { IconBook, IconShield, IconChart, IconLayers } from "./Icons";

export function Research() {
  const researchFoundations = [
    {
      id: "xfact",
      title: "X-Fact: A Large-Scale Multilingual Fact-Checking Benchmark",
      citation: "Gupta & Srikumar (ACL 2021)",
      objective: "Benchmarking factual claim verification across 25+ diverse world languages.",
      methodology:
        "Analyzed cross-lingual transfer of multilingual transformers on naturally occurring fact-check claims from journalistic organizations worldwide.",
      keyFinding:
        "Zero-shot classification performance drops significantly for morphologically rich and low-resource languages without language-specific syntactic grounding.",
      influence:
        "VeriTrace restricts scope strictly to English, Hindi, and Telugu rather than claiming universal multilingual capabilities without proven lexical coverage.",
    },
    {
      id: "fever",
      title: "FEVER: Fact Extraction and VERification",
      citation: "Thorne et al. (NAACL 2018)",
      objective: "Formulating fact verification as decoupled evidence sentence extraction and natural language inference (NLI).",
      methodology:
        "Evaluating two-stage pipelines: entity/sentence retrieval followed by 3-way entailment classification (SUPPORTS, REFUTES, NOT ENOUGH INFO).",
      keyFinding:
        "Classification models without evidence retrieval hallucinate justifications and succumb to spurious correlation artifacts in training text.",
      influence:
        "Directly inspired VeriTrace's decoupling: Evidence Retrieval is an independent stage from Evidence Comparison (NLI).",
    },
    {
      id: "averitec",
      title: "AVeriTeC: A Dataset for Real-World Claim Verification with Evidence",
      citation: "Schlichtkrull et al. (NeurIPS 2023)",
      objective: "Verifying complex real-world claims requiring search query generation and open-web multi-source synthesis.",
      methodology:
        "Curated real claims where evidence is scattered across multiple heterogeneous URLs, questions, and conflicting reports.",
      keyFinding:
        "Single-source verification fails in 43% of contentious claims. Real verification requires multi-source corroboration and conflict resolution.",
      influence:
        "VeriTrace's Decision Engine requires independent publisher clustering and checks for cross-source conflict rather than trusting single hits.",
    },
    {
      id: "calibration",
      title: "On Calibration of Modern Neural Networks",
      citation: "Guo et al. (ICML 2017)",
      objective: "Addressing overconfidence in deep neural network probability outputs.",
      methodology:
        "Evaluated temperature scaling, Platt scaling, and isotonic regression to align model confidence with empirical accuracy.",
      keyFinding:
        "Modern deep transformers are notoriously overconfident; uncalibrated softmax probabilities cannot be interpreted as posterior probabilities of truth.",
      influence:
        "VeriTrace applies post-hoc temperature scaling (T > 1.0) and separates 'Model Confidence' from 'Truth Probability'.",
    },
  ];

  return (
    <div className="research-view fade-in">
      <header className="research-header">
        <span className="editorial-section-tag">SCIENTIFIC FOUNDATIONS</span>
        <h1 className="research-title">METHODOLOGY &amp; RESEARCH</h1>
        <p className="research-subtitle">
          Why classification alone is insufficient, and how multilingual NLP and evidence retrieval ground verifiable AI assessments.
        </p>
      </header>

      {/* ── Model Transparency Panel ─────────────────────────────────── */}
      <section className="card methodology-panel">
        <div className="panel-header">
          <IconLayers className="panel-icon" />
          <div>
            <h2>Architectural Pipeline Trace</h2>
            <span className="panel-sub">Decoupled stages from raw input to calibrated explanation</span>
          </div>
        </div>

        <div className="pipeline-diagram-grid">
          {[
            { step: "01", name: "INPUT", desc: "Article, social post, or forwarded message" },
            { step: "02", name: "MULTILINGUAL NLP", desc: "Language identification & claimability boundary" },
            { step: "03", name: "CLAIM EXTRACTION", desc: "Isolating factual proposition & entities" },
            { step: "04", name: "EVIDENCE RETRIEVAL", desc: "External fact checks & official records" },
            { step: "05", name: "NLI COMPARISON", desc: "Cross-source entailment & contradiction" },
            { step: "06", name: "DECISION FUSION", desc: "Uncertainty-aware policy & temperature calibration" },
            { step: "07", name: "ASSESSMENT", desc: "Evidence trail, calibrated tier & explanation" },
          ].map((item, i) => (
            <div className="diagram-step-box" key={item.step}>
              <div className="step-num-circle">{item.step}</div>
              <strong>{item.name}</strong>
              <p>{item.desc}</p>
              {i < 6 && <span className="diagram-arrow">→</span>}
            </div>
          ))}
        </div>
      </section>

      {/* ── Key Theoretical Principles ───────────────────────────────── */}
      <section className="research-principles-grid">
        <div className="card principle-card">
          <div className="principle-head">
            <span className="principle-number">01</span>
            <h3>Classification Alone Is Insufficient</h3>
          </div>
          <p>
            Feeding an ungrounded claim to an LLM or sequence classifier invites hallucination. A model trained on past data cannot know whether an event that occurred yesterday actually took place. Verification must be anchored in fresh, verifiable external evidence.
          </p>
        </div>

        <div className="card principle-card">
          <div className="principle-number">02</div>
          <h3>Model Confidence ≠ Truth Probability</h3>
          <p>
            A high softmax probability only indicates that the model is certain of its internal classification pattern. It does not certify that the claim is an objective fact. VeriTrace explicitly labels confidence as model calibration, not truth certainty.
          </p>
        </div>

        <div className="card principle-card">
          <div className="principle-number">03</div>
          <h3>Multilingual Specificity</h3>
          <p>
            Language models perform disparately across typologically distinct languages. VeriTrace limits its operational scope strictly to English, Hindi, and Telugu, validating normalization and claimability specifically for these linguistic families.
          </p>
        </div>
      </section>

      {/* ── Peer-Reviewed Research Foundations Cards ─────────────────── */}
      <section className="research-cards-section">
        <div className="section-title-wrap">
          <IconBook className="section-icon" />
          <h2>Research Foundations</h2>
        </div>

        <div className="research-cards-grid">
          {researchFoundations.map((found) => (
            <div key={found.id} className="card foundation-card">
              <div className="foundation-top">
                <span className="foundation-citation">{found.citation}</span>
                <h3 className="foundation-title">{found.title}</h3>
              </div>

              <div className="foundation-body">
                <div className="foundation-field">
                  <strong>OBJECTIVE:</strong>
                  <span>{found.objective}</span>
                </div>

                <div className="foundation-field">
                  <strong>METHODOLOGY:</strong>
                  <span>{found.methodology}</span>
                </div>

                <div className="foundation-field">
                  <strong>KEY FINDING:</strong>
                  <span>{found.keyFinding}</span>
                </div>

                <div className="foundation-field highlight-field">
                  <strong>VERITRACE DESIGN INFLUENCE:</strong>
                  <span>{found.influence}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
