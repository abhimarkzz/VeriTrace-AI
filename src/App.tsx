import { useCallback, useState } from "react";
import { Landing } from "./components/Landing";
import { Pipeline } from "./components/Pipeline";
import { Result } from "./components/Result";
import { DEMO_PROMPTS } from "./mock/demoClaims";
import { VerificationError, verifyClaim } from "./services/mockVerificationService";
import { LANGUAGE_LABELS, type VerificationResult } from "./types";

type View = "home" | "verify" | "how" | "about";
type Phase = "idle" | "running" | "done";

const STEPS = [
  ["Detect", "Identify the language and the kind of input being checked."],
  ["Understand", "Extract the central factual claim from the surrounding text."],
  ["Retrieve", "Find sources that speak to that specific claim."],
  ["Compare", "Judge whether each source supports, contradicts or says too little."],
  ["Explain", "Show the assessment, the confidence, and the trail behind it."],
];

const NAV_ITEMS: [View, string][] = [
  ["home", "Home"],
  ["how", "How It Works"],
  ["about", "About"],
];

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="var(--accent)" strokeWidth="1.6" />
      <path d="M7.5 12.4l3 3 6-6.4" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function App() {
  const [view, setView] = useState<View>("home");
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [stageIndex, setStageIndex] = useState(0);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onVerify = useCallback(async () => {
    setError(null);
    setResult(null);
    setStageIndex(0);
    setPhase("running");
    try {
      const outcome = await verifyClaim(text, { onStage: (_, index) => setStageIndex(index) });
      setResult(outcome);
      setPhase("done");
    } catch (err) {
      setError(err instanceof VerificationError ? err.message : "Verification failed.");
      setPhase("idle");
    }
  }, [text]);

  const reset = () => {
    setResult(null);
    setPhase("idle");
    setText("");
    setError(null);
  };

  const go = (next: View) => {
    setView(next);
    if (next !== "verify") reset();
  };

  const showingResult = view === "verify" && phase === "done" && result !== null;

  return (
    <div
      className={
        view === "home" ? "shell shell-home" : showingResult ? "shell shell-plain" : "shell"
      }
    >
      <nav className="nav">
        <div className="container nav-inner">
          <button className="brand" onClick={() => go("home")}>
            <BrandMark />
            VeriTrace AI
          </button>
          <div className="nav-links">
            {NAV_ITEMS.map(([key, label]) => (
              <button
                key={key}
                onClick={() => go(key)}
                aria-current={view === key ? "page" : undefined}
              >
                {label}
              </button>
            ))}
            <button
              className="btn-nav-cta"
              onClick={() => {
                reset();
                setView("verify");
              }}
            >
              {showingResult ? "New Verification" : "Get Started"}
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" className="arrow">
                <path
                  d="M4 10h11M11 6l4 4-4 4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      <main>
        {view === "home" && <Landing onStart={() => go("verify")} />}
        <div className={showingResult ? "container container-wide" : "container"}>
          {view === "verify" && phase === "idle" && (
            <>
              <header className="hero fade-in">
                <span className="eyebrow">Prototype demonstration</span>
                <h1>Detect the claim. Trace the evidence.</h1>
                <p className="lede">
                  Most tools hand you a verdict. VeriTrace shows you the claim it found, the
                  sources it traced, and how each one relates to that claim.
                </p>
              </header>

              <section className="card composer fade-in">
                <textarea
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  placeholder="Paste a news article, social media post, or forwarded message…"
                  aria-label="Text to verify"
                />
                <div className="composer-row">
                  <select defaultValue="auto" aria-label="Language">
                    <option value="auto">Auto-detect language</option>
                    {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                      <option key={code} value={code}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <span className="hint">English, Hindi and Telugu</span>
                  <span className="spacer" />
                  <button
                    className="btn btn-primary"
                    onClick={onVerify}
                    disabled={text.trim().length === 0}
                  >
                    Verify claim
                  </button>
                </div>
                {error && <p className="error-text">{error}</p>}
              </section>

              <section className="demos fade-in">
                <div className="demos-label">Try a demo claim</div>
                <div className="chips">
                  {DEMO_PROMPTS.map((demo) => (
                    <button
                      key={demo.id}
                      className="chip"
                      onClick={() => {
                        setText(demo.text);
                        setError(null);
                      }}
                    >
                      {demo.label}
                      <span className="chip-lang">{LANGUAGE_LABELS[demo.language]}</span>
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}

          {view === "verify" && phase === "running" && <Pipeline activeIndex={stageIndex} />}

          {view === "verify" && phase === "done" && result && <Result result={result} />}

          {view === "how" && (
            <section className="fade-in">
              <header className="hero">
                <h1>How it works</h1>
                <p className="lede">
                  Five stages, each answering exactly one question.
                </p>
              </header>
              <div className="card">
                <div className="steps">
                  {STEPS.map(([title, body], index) => (
                    <div className="step" key={title}>
                      <div className="step-num">{index + 1}</div>
                      <div>
                        <h3>{title}</h3>
                        <p>{body}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <p className="notice" style={{ marginTop: 18 }}>
                <strong>Separation matters.</strong> Retrieval decides what evidence exists.
                A separate comparison step decides what that evidence means. Only then is a
                verdict formed — so every assessment can be traced back to the sources behind it.
              </p>
            </section>
          )}

          {view === "about" && (
            <section className="fade-in prose">
              <header className="hero">
                <h1>About this prototype</h1>
              </header>
              <div className="card">
                <p style={{ marginTop: 0 }}>
                  VeriTrace AI addresses a gap in how misinformation tools communicate. A bare
                  “false” label asks the reader to trust the tool. An evidence trail lets them
                  check it.
                </p>
                <p>
                  The interface is built around claims rather than whole articles, covers
                  English, Hindi and Telugu, and treats uncertainty as a first-class outcome:
                  “insufficient evidence” is a legitimate answer, not a failure.
                </p>
                <p style={{ marginBottom: 0 }}>
                  Every assessment separates what was <em>found</em> from what it{" "}
                  <em>means</em> — the same separation the underlying architecture is designed
                  around.
                </p>
              </div>
              <p className="notice" style={{ marginTop: 18 }}>
                <strong>This is a demonstration prototype.</strong> It walks through the
                intended workflow using a fixed set of prepared examples. It does not perform
                live web search or run a model, and it should not be used to check real claims.
                Linked sources are real and can be opened; the scores shown are illustrative.
              </p>
            </section>
          )}
        </div>
      </main>

      <footer>
        <div className="container">
          VeriTrace AI — prototype demonstration. Not a live fact-checking service.
        </div>
      </footer>
    </div>
  );
}
