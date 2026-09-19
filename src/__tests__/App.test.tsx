import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import App from "../App";
import * as verificationService from "../services/verificationService";
import type { VerificationResult } from "../types";

// Mock verification service
vi.mock("../services/verificationService", async () => {
  const actual = await vi.importActual<typeof verificationService>("../services/verificationService");
  return {
    ...actual,
    verifyClaim: vi.fn(),
  };
});

const mockSuccessResult: VerificationResult = {
  analysisId: "test-ana-1",
  claim: "UPI transaction limit has been reduced to 500.",
  language: "en",
  assessment: "SUPPORTED",
  confidence: 0.94,
  confidenceTier: "HIGH",
  evidenceStrength: "STRONG",
  claimType: "Factual claim",
  explanation: "Official regulatory documentation confirms the revision to transaction parameters.",
  confidenceExplanation: "High confidence supported by multiple verified citations.",
  confidenceBreakdown: {
    evidenceAgreement: 0.95,
    evidenceRelevance: 0.92,
    sourceQuality: 0.9,
    modelConfidence: 0.94,
  },
  evidence: [
    {
      id: "ev-1",
      source: "National Payments Corporation",
      publisher: "NPCI Official",
      title: "Revised Limits Circular 2024",
      url: "https://npci.org.in/circular-2024",
      snippet: "Parameters for peer-to-merchant transactions have been calibrated.",
      relation: "SUPPORT",
      relevanceScore: 0.96,
      sourceQuality: 0.95,
      publishedAt: "2024-03-15T00:00:00Z",
    },
  ],
};

const mockInsufficientResult: VerificationResult = {
  analysisId: "test-ana-2",
  claim: "Ancient temple contains alien artifacts.",
  language: "en",
  assessment: "INSUFFICIENT_EVIDENCE",
  confidence: 0.35,
  confidenceTier: "LOW",
  claimType: "Speculative claim",
  explanation: "No verifiable primary sources or scientific databases support this claim.",
  evidence: [],
};

const mockConflictingResult: VerificationResult = {
  analysisId: "test-ana-3",
  claim: "School holidays announced for the entire month.",
  language: "en",
  assessment: "CONFLICTING_EVIDENCE",
  confidence: 0.5,
  confidenceTier: "MEDIUM",
  evidenceStrength: "MODERATE",
  claimType: "Factual claim",
  explanation: "Contradictory notices were issued by different regional district authorities.",
  evidence: [
    {
      id: "ev-c1",
      source: "District A Notice",
      title: "Holiday declared in District A",
      url: "https://example.com/dist-a",
      snippet: "Schools closed due to weather.",
      relation: "SUPPORT",
      relevanceScore: 0.85,
      sourceQuality: 0.8,
    },
    {
      id: "ev-c2",
      source: "Ministry of Education",
      title: "No national school closure order",
      url: "https://example.com/min-edu",
      snippet: "National ministry denies blanket closure rumors.",
      relation: "CONTRADICT",
      relevanceScore: 0.9,
      sourceQuality: 0.95,
    },
  ],
};

describe("VeriTrace AI Frontend — Complete UI Flow and States", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Landing page with hero, mission and CTA button", () => {
    render(<App />);

    expect(screen.getByText(/VERIFY WHAT/i)).toBeInTheDocument();
    expect(screen.getByText(/MULTILINGUAL EVIDENCE INTELLIGENCE/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i }).length).toBeGreaterThan(0);
    expect(screen.getByText(/THE VERIFICATION GAP/i)).toBeInTheDocument();
    expect(screen.getByText(/FROM A VERDICT/i)).toBeInTheDocument();
  });

  it("navigates to verification composer when clicking CTA or nav items", () => {
    render(<App />);

    const cta = screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0];
    fireEvent.click(cta);

    expect(screen.getByPlaceholderText(/Paste a news article/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Verify claim/i })).toBeInTheDocument();
  });

  it("validates input: disables submit button on empty or whitespace text", () => {
    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    const submitBtn = screen.getByRole("button", { name: /Verify claim/i });

    // Initially empty
    expect(submitBtn).toBeDisabled();

    // Whitespace only
    fireEvent.change(textarea, { target: { value: "    " } });
    expect(submitBtn).toBeDisabled();

    // Valid text enables button
    fireEvent.change(textarea, { target: { value: "New government advisory issued." } });
    expect(submitBtn).not.toBeDisabled();
  });

  it("handles language selection dropdown and sample prompt chips", () => {
    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const select = screen.getByLabelText(/Language/i);
    fireEvent.change(select, { target: { value: "te" } });
    expect(select).toHaveValue("te");

    // Click sample claim chip
    const chips = screen.getAllByRole("button", { name: /Try sample claim/i });
    expect(chips.length).toBeGreaterThan(0);
    fireEvent.click(chips[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    expect((textarea as HTMLTextAreaElement).value.length).toBeGreaterThan(0);
  });

  it("displays pipeline progression and loading state during submission", async () => {
    let resolveVerify: (val: VerificationResult) => void;
    const verifyPromise = new Promise<VerificationResult>((resolve) => {
      resolveVerify = resolve;
    });

    vi.mocked(verificationService.verifyClaim).mockImplementation(async (_text, options) => {
      options?.onStage?.("Detecting language", 1);
      return verifyPromise;
    });

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "RBI issues new banking guideline." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    // Pipeline should now be visible
    expect(screen.getByText(/INVESTIGATING CLAIM IN REAL TIME/i)).toBeInTheDocument();

    // Resolve verify
    await act(async () => {
      resolveVerify!(mockSuccessResult);
    });

    await waitFor(() => {
      expect(document.querySelector("h1.verdict-name")).toHaveTextContent(/Supported/i);
    });
  });

  it("renders successful result with verdict, confidence, breakdown, and evidence cards", async () => {
    vi.mocked(verificationService.verifyClaim).mockResolvedValueOnce(mockSuccessResult);

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "UPI transaction limit has been reduced to 500." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(document.querySelector("h1.verdict-name")).toHaveTextContent(/Supported/i);
    });

    // Check tier
    expect(screen.getAllByText("HIGH").length).toBeGreaterThan(0);

    // Check evidence title
    expect(screen.getAllByText(/Revised Limits Circular 2024/i)[0]).toBeInTheDocument();

    // Check publisher
    expect(screen.getAllByText(/NPCI Official/i)[0]).toBeInTheDocument();

    // Verify evidence link attributes
    const extLinks = screen.getAllByRole("link", { name: /Open NPCI Official|Open source/i });
    expect(extLinks.length).toBeGreaterThan(0);
    expect(extLinks[0]).toHaveAttribute("target", "_blank");
    expect(extLinks[0]).toHaveAttribute("href", "https://npci.org.in/circular-2024");
  });

  it("renders INSUFFICIENT_EVIDENCE result properly", async () => {
    vi.mocked(verificationService.verifyClaim).mockResolvedValueOnce(mockInsufficientResult);

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "Ancient temple alien artifacts." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(document.querySelector("h1.verdict-name")).toHaveTextContent(/Insufficient evidence/i);
      expect(screen.getByText(/No verifiable external fact-checking sources were traced/i)).toBeInTheDocument();
    });
  });

  it("renders CONFLICTING_EVIDENCE result properly", async () => {
    vi.mocked(verificationService.verifyClaim).mockResolvedValueOnce(mockConflictingResult);

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "School holidays announced." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(document.querySelector("h1.verdict-name")).toHaveTextContent(/Conflicting evidence/i);
      expect(screen.getAllByText(/Holiday declared in District A/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/No national school closure order/i)[0]).toBeInTheDocument();
    });
  });

  it("handles backend error with alert banner and retry option", async () => {
    vi.mocked(verificationService.verifyClaim).mockRejectedValueOnce(
      new Error("Backend verification service is currently unreachable. Please ensure the FastAPI server is running.")
    );

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "Network failure test." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/Backend verification service is currently unreachable/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Try again/i })).toBeInTheDocument();
  });

  it("handles timeout error gracefully", async () => {
    vi.mocked(verificationService.verifyClaim).mockRejectedValueOnce(
      new Error("The verification request timed out. The server may be processing heavy models or unreachable.")
    );

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "Timeout simulation test." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/The verification request timed out/i)).toBeInTheDocument();
    });
  });

  it("handles unsupported language error banner", async () => {
    vi.mocked(verificationService.verifyClaim).mockRejectedValueOnce(
      new Error("Unsupported language detected. VeriTrace AI currently verifies claims in English, Hindi, and Telugu.")
    );

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "Bonjour tout le monde." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/Unsupported language detected/i)).toBeInTheDocument();
    });
  });

  it("resets result and allows running another analysis", async () => {
    vi.mocked(verificationService.verifyClaim).mockResolvedValueOnce(mockSuccessResult);

    render(<App />);
    fireEvent.click(screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0]);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, { target: { value: "Claim to reset." } });
    fireEvent.click(screen.getByRole("button", { name: /Verify claim/i }));

    await waitFor(() => {
      expect(document.querySelector("h1.verdict-name")).toHaveTextContent(/Supported/i);
    });

    const resetBtn = screen.getByRole("button", { name: /Run another analysis/i });
    fireEvent.click(resetBtn);

    // Should be back at empty composer
    expect(screen.getByPlaceholderText(/Paste a news article/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Supported by evidence/i })).not.toBeInTheDocument();
  });

  it("renders Research, Evidence, and About sections via navigation", () => {
    render(<App />);

    // Navigate to Research
    fireEvent.click(screen.getAllByRole("button", { name: /Research/i })[0]);
    expect(screen.getByRole("heading", { name: /Methodology & Research/i })).toBeInTheDocument();
    expect(screen.getByText(/X-Fact/i)).toBeInTheDocument();

    // Navigate to About
    fireEvent.click(screen.getAllByRole("button", { name: /About/i })[0]);
    expect(screen.getByRole("heading", { name: /Why VeriTrace Exists/i })).toBeInTheDocument();
    expect(screen.getAllByText(/Assessment, not absolute truth/i).length).toBeGreaterThan(0);

    // Navigate to Evidence
    fireEvent.click(screen.getAllByRole("button", { name: /Evidence/i })[0]);
    expect(screen.getByRole("heading", { name: /Trace the Evidence/i })).toBeInTheDocument();
  });
});
