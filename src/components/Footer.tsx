import { BrandMark, BrandLogo, type NavView } from "./Navigation";

interface FooterProps {
  onNavigate: (view: NavView) => void;
}

export function Footer({ onNavigate }: FooterProps) {
  return (
    <footer className="editorial-footer">
      <div className="container footer-inner">
        <div className="footer-top">
          <div className="footer-brand-col">
            <div className="footer-brand">
              <BrandLogo height={32} className="footer-logo-img" />
              <span className="brand-text sr-only">
                VeriTrace <span className="brand-suffix">AI</span>
              </span>
            </div>
            <p className="footer-tagline">
              Detect the claim. Trace the evidence. An AI-assisted investigation studio for multilingual misinformation detection.
            </p>
            <div className="footer-languages">
              <span className="lang-pill">English</span>
              <span className="lang-pill">Hindi (हिंदी)</span>
              <span className="lang-pill">Telugu (తెలుగు)</span>
            </div>
          </div>

          <div className="footer-links-col">
            <div className="links-group">
              <strong>Navigation</strong>
              <button onClick={() => onNavigate("home")}>Home</button>
              <button onClick={() => onNavigate("analyze")}>Analyze a Claim</button>
              <button onClick={() => onNavigate("evidence")}>Evidence Explorer</button>
              <button onClick={() => onNavigate("intelligence")}>System Intelligence</button>
            </div>

            <div className="links-group">
              <strong>Foundations</strong>
              <button onClick={() => onNavigate("about")}>About &amp; Methodology</button>
              <a
                href="/api/docs"
                target="_blank"
                rel="noreferrer"
              >
                API Documentation (FastAPI)
              </a>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="responsible-ai-note">
            <strong>Responsible AI Principle:</strong> Assessment, not absolute truth. Model confidence reflects internal prediction strength; it does not guarantee factual certainty. Citations should be reviewed independently.
          </div>
          <div className="copyright-note">
            VeriTrace AI · Neural Stream · Problem N5
          </div>
        </div>
      </div>
    </footer>
  );
}
