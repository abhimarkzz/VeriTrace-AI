import { useCallback, useState, useEffect } from "react";
import { Navigation, type NavView } from "./components/Navigation";
import { Home } from "./components/Home";
import { AnalyzeWorkspace } from "./components/AnalyzeWorkspace";
import { Result } from "./components/Result";
import { EvidenceExplorer } from "./components/EvidenceExplorer";
import { Intelligence } from "./components/Intelligence";
import { Research } from "./components/Research";
import { About } from "./components/About";
import { Footer } from "./components/Footer";
import { verifyClaim, fetchAnalysisById } from "./services/verificationService";
import type { Language, VerificationResult } from "./types";

type Phase = "idle" | "running" | "done";

export default function App() {
  const [view, setView] = useState<NavView>("home");
  const [phase, setPhase] = useState<Phase>("idle");
  const [presetText, setPresetText] = useState<string>("");
  const [presetLang, setPresetLang] = useState<string>("auto");
  const [stageIndex, setStageIndex] = useState(0);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sync with browser URL search parameters if available
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const analysisId = params.get("id") || params.get("analysis_id");
    if (analysisId) {
      fetchAnalysisById(analysisId)
        .then((res) => {
          setResult(res);
          setPhase("done");
          setView("analyze");
        })
        .catch(() => {
          // Ignore invalid URL param
        });
    }
  }, []);

  const handleVerify = useCallback(async (text: string, language: string) => {
    setError(null);
    setResult(null);
    setStageIndex(0);
    setPhase("running");

    try {
      const outcome = await verifyClaim(text, {
        language,
        onStage: (_, index) => setStageIndex(index),
      });
      setResult(outcome);
      setPhase("done");
      // Update history in URL without reloading
      if (outcome.analysisId) {
        window.history.replaceState(null, "", `?id=${encodeURIComponent(outcome.analysisId)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification request failed.");
      setPhase("idle");
    }
  }, []);

  const resetAnalysis = () => {
    setResult(null);
    setPhase("idle");
    setPresetText("");
    setPresetLang("auto");
    setError(null);
    window.history.replaceState(null, "", window.location.pathname);
  };

  const handleNavigate = (nextView: NavView) => {
    setView(nextView);
    if (nextView !== "analyze") {
      resetAnalysis();
    }
  };

  const handleSelectPreset = (text?: string, lang?: Language) => {
    if (text) setPresetText(text);
    if (lang) setPresetLang(lang);
    setResult(null);
    setPhase("idle");
    setError(null);
    setView("analyze");
  };

  const handleSelectHistoricalAnalysis = (storedResult: VerificationResult) => {
    setResult(storedResult);
    setPhase("done");
    setView("analyze");
    if (storedResult.analysisId) {
      window.history.replaceState(null, "", `?id=${encodeURIComponent(storedResult.analysisId)}`);
    }
  };

  const isShowingResult = view === "analyze" && phase === "done" && result !== null;

  return (
    <div className={`app-shell view-${view} ${isShowingResult ? "state-result" : ""}`}>
      {/* Global Navigation */}
      <Navigation
        currentView={view}
        onNavigate={handleNavigate}
        onNewAnalysis={() => {
          resetAnalysis();
          setView("analyze");
        }}
        isResultActive={isShowingResult}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {view === "home" && (
          <Home
            onAnalyzeClaim={handleSelectPreset}
            onExploreEvidence={() => handleNavigate("evidence")}
          />
        )}

        {view === "analyze" && !isShowingResult && (
          <div className="container workspace-wrapper">
            <AnalyzeWorkspace
              initialText={presetText}
              initialLanguage={presetLang}
              onVerify={handleVerify}
              isLoading={phase === "running"}
              currentStageIndex={stageIndex}
              error={error}
              onClearError={() => setError(null)}
            />
          </div>
        )}

        {isShowingResult && result && (
          <div className="container container-wide">
            <Result
              result={result}
              onReset={() => {
                resetAnalysis();
                setView("analyze");
              }}
            />
          </div>
        )}

        {view === "evidence" && (
          <div className="container">
            <EvidenceExplorer onAnalyzeClaim={handleSelectPreset} />
          </div>
        )}

        {view === "intelligence" && (
          <div className="container">
            <Intelligence
              onSelectAnalysis={handleSelectHistoricalAnalysis}
              onNavigateAnalyze={() => {
                resetAnalysis();
                setView("analyze");
              }}
            />
          </div>
        )}

        {view === "research" && (
          <div className="container">
            <Research />
          </div>
        )}

        {view === "about" && (
          <div className="container">
            <About />
          </div>
        )}
      </main>

      {/* Editorial Footer */}
      <Footer onNavigate={handleNavigate} />
    </div>
  );
}
