const ARROW = (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" className="arrow">
    <path d="M4 10h11M11 6l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const FEATURES = [
  {
    title: "Multilingual",
    body: "Multiple languages, one mission",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3z" />
      </>
    ),
  },
  {
    title: "Evidence-Backed",
    body: "Every claim, every source",
    icon: (
      <>
        <path d="M6 3h7l5 5v13H6z" />
        <path d="M13 3v5h5M9 13h6M9 17h6" />
      </>
    ),
  },
  {
    title: "AI-Powered",
    body: "Advanced analysis, clear results",
    icon: (
      <>
        <rect x="7" y="7" width="10" height="10" rx="1.5" />
        <path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4" />
      </>
    ),
  },
  {
    title: "For a Safer Tomorrow",
    body: "A more informed world",
    icon: (
      <>
        <path d="M12 3l7 3v6c0 4.4-2.9 7.9-7 9-4.1-1.1-7-4.6-7-9V6z" />
        <path d="M9 12l2.2 2.2L15.5 10" />
      </>
    ),
  },
];

export function Landing({ onStart }: { onStart: () => void }) {
  return (
    <section className="landing">
      <div className="landing-inner">
        <div className="landing-top">
          <h1 className="landing-title">
            In a world of endless information,
            <span className="landing-title-accent">what&rsquo;s the truth?</span>
          </h1>
          <p className="landing-lede">
            VeriTrace AI helps you cut through the noise, detect misinformation,
            <br />
            and trace every claim back to evidence.
          </p>
        </div>

        <div className="landing-bottom">
          <button className="landing-cta" onClick={onStart}>
            Begin Your Verification {ARROW}
          </button>
          <p className="landing-tagline">
            Others give you the verdict.
            <br />
            We give you the verdict and the evidence trail.
          </p>

          <ul className="landing-features">
            {FEATURES.map((feature) => (
              <li key={feature.title}>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  {feature.icon}
                </svg>
                <div>
                  <strong>{feature.title}</strong>
                  <span>{feature.body}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
