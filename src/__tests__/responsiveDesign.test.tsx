import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Navigation } from "../components/Navigation";
import { Home } from "../components/Home";
import { AnalyzeWorkspace } from "../components/AnalyzeWorkspace";
import { Result } from "../components/Result";
import type { VerificationResult } from "../types";

describe("Responsive Design & Mobile Ergonomics Suite", () => {
  it("renders mobile hamburger button with accessible labels and closed state", () => {
    const handleNavigate = vi.fn();
    render(<Navigation currentView="home" onNavigate={handleNavigate} />);

    const toggleBtn = screen.getByRole("button", { name: /Open menu/i });
    expect(toggleBtn).toBeInTheDocument();
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");
  });

  it("opens mobile drawer upon tapping hamburger, displays all navigation links, and handles navigation", () => {
    const handleNavigate = vi.fn();
    render(<Navigation currentView="home" onNavigate={handleNavigate} />);

    const toggleBtn = screen.getByRole("button", { name: /Open menu/i });
    fireEvent.click(toggleBtn);

    // Drawer is now open
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(toggleBtn).toHaveAttribute("aria-expanded", "true");

    // All links inside drawer are accessible
    const aboutBtns = screen.getAllByText(/About/i);
    expect(aboutBtns.length).toBeGreaterThanOrEqual(1);

    // Clicking a mobile link triggers navigation and closes the drawer
    fireEvent.click(aboutBtns[aboutBtns.length - 1]);
    expect(handleNavigate).toHaveBeenCalledWith("about");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes mobile drawer when Escape key is pressed", () => {
    const handleNavigate = vi.fn();
    render(<Navigation currentView="home" onNavigate={handleNavigate} />);

    const toggleBtn = screen.getByRole("button", { name: /Open menu/i });
    fireEvent.click(toggleBtn);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders Home view responsive hero, flow steps, and call-to-actions cleanly", () => {
    const handleAnalyze = vi.fn();
    const handleExplore = vi.fn();
    render(<Home onAnalyzeClaim={handleAnalyze} onExploreEvidence={handleExplore} />);

    expect(screen.getByText(/VERIFY WHAT/i)).toBeInTheDocument();
    expect(screen.getByText(/MULTILINGUAL EVIDENCE INTELLIGENCE/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Begin Your Verification/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Explore Evidence/i })).toBeInTheDocument();

    // Verification pipeline flow steps render
    expect(screen.getByText(/VERITRACE PIPELINE/i)).toBeInTheDocument();
    expect(screen.getAllByText(/CLAIM/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/EVIDENCE/i).length).toBeGreaterThanOrEqual(1);
  });

  it("renders AnalyzeWorkspace with responsive input elements and mode tabs", () => {
    const handleVerify = vi.fn().mockResolvedValue(undefined);
    const handleClear = vi.fn();
    render(
      <AnalyzeWorkspace
        onVerify={handleVerify}
        isLoading={false}
        currentStageIndex={0}
        error={null}
        onClearError={handleClear}
      />,
    );

    const textarea = screen.getByRole("textbox", { name: /Text to verify/i });
    expect(textarea).toBeInTheDocument();

    // Mode tabs exist and switch active mode
    const articleTab = screen.getByRole("tab", { name: /NEWS ARTICLE/i });
    fireEvent.click(articleTab);
    expect(articleTab).toHaveClass("active");

    // Typing into textarea updates character count
    fireEvent.change(textarea, { target: { value: "Heavy rains caused flooding across Kathmandu Valley." } });
    expect(screen.getByText(/52 characters/i)).toBeInTheDocument();

    // Submit button works
    const submitBtn = screen.getByRole("button", { name: /Verify claim/i });
    expect(submitBtn).toBeInTheDocument();
  });

  it("renders Result view responsive telemetry and citation cards with full accessibility", () => {
    const handleReset = vi.fn();
    const mockResult: VerificationResult = {
      analysisId: "resp-test-01",
      assessment: "SUPPORTED",
      confidence: 0.88,
      confidenceTier: "HIGH CONFIDENCE",
      language: "en",
      claimType: "factual",
      claim: "Nepal floods triggered state of emergency in affected districts.",
      explanation: "Independent reports confirm official emergency declarations following monsoon floods.",
      evidenceStrength: "STRONG",
      evidence: [
        {
          id: "ev-1",
          source: "news",
          title: "Kathmandu Valley Inundated by Record Rainfall",
          snippet: "Official relief teams deployed as rivers burst banks across Kathmandu.",
          url: "https://example.com/nepal-floods",
          publisher: "The Himalayan Times",
          publishedAt: "2026-09-18T10:00:00Z",
          relation: "SUPPORT",
          relevanceScore: 0.92,
          sourceQuality: 0.95,
        },
      ],
      confidenceBreakdown: {
        evidenceAgreement: 0.92,
        evidenceRelevance: 0.9,
        sourceQuality: 0.95,
        modelConfidence: 0.88,
      },
    };

    render(<Result result={mockResult} onReset={handleReset} />);

    expect(screen.getByRole("heading", { name: /Supported by evidence/i })).toBeInTheDocument();
    expect(screen.getByText(/HIGH CONFIDENCE/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Kathmandu Valley Inundated by Record Rainfall/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /Run another analysis/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copy result summary to clipboard/i })).toBeInTheDocument();
  });
});
