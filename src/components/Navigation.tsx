import { useState, useEffect } from "react";
import { IconArrow } from "./Icons";

export type NavView = "home" | "analyze" | "evidence" | "intelligence" | "about";

interface NavigationProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  onNewAnalysis?: () => void;
  isResultActive?: boolean;
}

export function BrandMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src="/veritrace-icon.png"
      alt="VeriTrace AI Icon"
      className={`brand-mark ${className}`.trim()}
      width={size}
      height={size}
      style={{
        width: size,
        height: size,
        objectFit: "contain",
        flexShrink: 0,
        display: "inline-block",
      }}
    />
  );
}

export function BrandLogo({ height = 22, className = "" }: { height?: number; className?: string }) {
  return (
    <picture className={`brand-logo-picture ${className}`.trim()}>
      <source srcSet="/veritrace-logo-dark.png" media="(prefers-color-scheme: dark)" />
      <img
        src="/veritrace-logo.png"
        alt="VeriTrace AI"
        className="brand-logo-img"
        height={height}
        style={{
          height,
          width: "auto",
          objectFit: "contain",
          display: "inline-block",
          verticalAlign: "middle",
        }}
      />
    </picture>
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

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") setMobileOpen(false);
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "";
        window.removeEventListener("keydown", handleKeyDown);
      };
    } else {
      document.body.style.overflow = "";
    }
  }, [mobileOpen]);

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
          <BrandMark size={28} />
          <BrandLogo height={22} className="brand-logo-header" />
          <span className="brand-name sr-only">
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
