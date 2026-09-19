import { useState } from "react";
import { IconArrow } from "./Icons";

export type NavView = "home" | "analyze" | "evidence" | "intelligence" | "about";

interface NavigationProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  onNewAnalysis?: () => void;
  isResultActive?: boolean;
}

export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ width: 22, height: 22, flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" stroke="var(--accent)" strokeWidth="1.6" />
      <path
        d="M7.5 12.4l3 3 6-6.4"
        stroke="var(--accent)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const NAV_LINKS: Array<{ id: NavView; label: string }> = [
  { id: "home", label: "Home" },
  { id: "evidence", label: "Evidence Explorer" },
  { id: "intelligence", label: "Intelligence" },
  { id: "about", label: "About" },
];

export function Navigation({
  currentView,
  onNavigate,
  onNewAnalysis,
  isResultActive = false,
}: NavigationProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleNavClick = (view: NavView) => {
    setMobileOpen(false);
    onNavigate(view);
  };

  return (
    <header className="global-nav">
      <div className="container nav-inner">
        {/* Brand */}
        <button
          className="brand-link"
          onClick={() => handleNavClick("home")}
          aria-label="VeriTrace AI Home"
        >
          <BrandMark />
          <span className="brand-name">
            VeriTrace <span className="brand-suffix">AI</span>
          </span>
        </button>

        {/* Desktop Links */}
        <nav className="desktop-links" aria-label="Main Navigation">
          {NAV_LINKS.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${currentView === item.id ? "active" : ""}`}
              onClick={() => handleNavClick(item.id)}
              aria-current={currentView === item.id ? "page" : undefined}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Primary CTA */}
        <div className="nav-actions">
          <button
            className="btn-nav-primary"
            onClick={() => {
              if (onNewAnalysis) {
                onNewAnalysis();
              } else {
                handleNavClick("analyze");
              }
            }}
          >
            <span>{isResultActive ? "New Verification" : "Analyze a Claim"}</span>
            <IconArrow className="arrow-icon" />
          </button>

          {/* Mobile Hamburger */}
          <button
            className="mobile-toggle"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
          >
            <span className={`hamburger ${mobileOpen ? "open" : ""}`}>
              <span />
              <span />
              <span />
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="mobile-drawer" role="dialog" aria-modal="true">
          <div className="mobile-drawer-inner">
            <div className="mobile-links">
              {NAV_LINKS.map((item) => (
                <button
                  key={item.id}
                  className={`mobile-link ${currentView === item.id ? "active" : ""}`}
                  onClick={() => handleNavClick(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="mobile-cta-wrap">
              <button
                className="btn-nav-primary full-width"
                onClick={() => {
                  setMobileOpen(false);
                  if (onNewAnalysis) {
                    onNewAnalysis();
                  } else {
                    handleNavClick("analyze");
                  }
                }}
              >
                <span>{isResultActive ? "New Verification" : "Analyze a Claim"}</span>
                <IconArrow className="arrow-icon" />
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
