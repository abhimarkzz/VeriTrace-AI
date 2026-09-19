import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import * as verificationService from "../services/verificationService";
import type { VerificationResult } from "../types";

vi.mock("../services/verificationService", async () => {
  const actual = await vi.importActual<typeof verificationService>(
    "../services/verificationService"
  );
  return {
    ...actual,
    verifyClaim: vi.fn(),
  };
});

const enSupportedResult: VerificationResult = {
  analysisId: "e2e-en-001",
  claim: "RBI maintains repo rate at 6.5 percent.",
  language: "en",
  assessment: "SUPPORTED",
  confidence: 0.92,
  confidenceTier: "HIGH",
  evidenceStrength: "STRONG",
  claimType: "Financial statistic",
  explanation: "Official Reserve Bank of India policy statement validates the rate maintenance.",
  confidenceExplanation: "High agreement among central banking sources.",
  confidenceBreakdown: {
    evidenceAgreement: 0.95,
    evidenceRelevance: 0.94,
    sourceQuality: 0.92,
    modelConfidence: 0.88,
  },
  evidence: [
    {
      id: "ev-en-1",
      source: "Reserve Bank of India",
      publisher: "RBI Official",
      title: "Monetary Policy Statement February 2024",
      url: "https://rbi.org.in/press/2024",
      snippet: "The Monetary Policy Committee decided to keep the policy repo rate unchanged at 6.50 percent.",
      relation: "SUPPORT",
      relevanceScore: 0.97,
      sourceQuality: 0.95,
      publishedAt: "2024-02-08T10:00:00Z",
    },
  ],
};

const hiInsufficientResult: VerificationResult = {
  analysisId: "e2e-hi-002",
  claim: "जंगल में अज्ञात उड़नतश्तरी देखी गई।",
  language: "hi",
  assessment: "INSUFFICIENT_EVIDENCE",
  confidence: 0.25,
  confidenceTier: "LOW",
  claimType: "Unverified viral rumor",
  explanation: "इस दावे के समर्थन में कोई विश्वसनीय तथ्य-जांच या सरकारी रिकॉर्ड उपलब्ध नहीं है।",
  evidence: [],
};

const teConflictingResult: VerificationResult = {
  analysisId: "e2e-te-003",
  claim: "నగరంలో మెట్రో రైలు సర్వీసులు రేపటి నుంచి నిలిపివేత.",
  language: "te",
  assessment: "CONFLICTING_EVIDENCE",
  confidence: 0.52,
  confidenceTier: "MEDIUM",
  evidenceStrength: "MODERATE",
  claimType: "Civic announcement",
  explanation: "వివిధ అధికారిక విభాగాల నుంచి పరస్పర విరుద్ధమైన ప్రకటనలు వెలువడ్డాయి.",
  evidence: [
    {
      id: "ev-te-1",
      source: "Metro Rail Authority",
      publisher: "HMRL",
      title: "Clarification on Metro Operations",
      url: "https://hmrl.gov.in/notice",
      snippet: "Reports claiming complete shutdown of metro services are unfounded.",
      relation: "CONTRADICT",
      relevanceScore: 0.92,
      sourceQuality: 0.94,
    },
    {
      id: "ev-te-2",
      source: "Local News Daily",
      publisher: "City News",
      title: "Maintenance Work on Line 1",
      url: "https://citynews.in/line1-maintenance",
      snippet: "Partial maintenance scheduled on select corridors tomorrow morning.",
      relation: "SUPPORT",
      relevanceScore: 0.81,
      sourceQuality: 0.72,
    },
  ],
};

describe("End-to-End Multilingual Verification Workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles consecutive multi-turn verifications across English, Hindi, and Telugu", async () => {
    const mockVerify = vi.mocked(verificationService.verifyClaim);

    render(<App />);

    // Click CTA to navigate to composer
    const cta = screen.getAllByRole("button", { name: /Analyze a Claim|Begin Your Verification/i })[0];
    fireEvent.click(cta);

    // ── Turn 1: English Supported Claim ─────────────────────────────────────
    mockVerify.mockResolvedValueOnce(enSupportedResult);

    const textarea = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea, {
      target: { value: "RBI maintains repo rate at 6.5 percent." },
    });

    const submitBtn = screen.getByRole("button", { name: /Verify Claim/i });
    fireEvent.click(submitBtn);

    // Wait for Result view
    await waitFor(() => {
      const verdict = document.querySelector("h1.verdict-name");
      expect(verdict).toBeInTheDocument();
      expect(verdict).toHaveTextContent(/Supported/i);
    });

    // Check high confidence badge & evidence
    expect(screen.getAllByText("HIGH").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Monetary Policy Statement February 2024").length).toBeGreaterThan(0);

    // Reset back to input
    const newClaimBtn = screen.getAllByRole("button", { name: /Run another analysis|New Verification/i })[0];
    fireEvent.click(newClaimBtn);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Paste a news article/i)).toBeInTheDocument();
    });

    // ── Turn 2: Hindi Insufficient Evidence Claim ───────────────────────────
    mockVerify.mockResolvedValueOnce(hiInsufficientResult);

    const textarea2 = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea2, {
      target: { value: "जंगल में अज्ञात उड़नतश्तरी देखी गई।" },
    });

    // Select Hindi language
    const langSelect = screen.getByRole("combobox");
    fireEvent.change(langSelect, { target: { value: "hi" } });

    const submitBtn2 = screen.getByRole("button", { name: /Verify Claim/i });
    fireEvent.click(submitBtn2);

    await waitFor(() => {
      const verdict = document.querySelector("h1.verdict-name");
      expect(verdict).toBeInTheDocument();
      expect(verdict).toHaveTextContent(/Insufficient/i);
    });

    expect(screen.getAllByText("LOW").length).toBeGreaterThan(0);

    // Reset back to input
    const newClaimBtn2 = screen.getAllByRole("button", { name: /Run another analysis|New Verification/i })[0];
    fireEvent.click(newClaimBtn2);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Paste a news article/i)).toBeInTheDocument();
    });

    // ── Turn 3: Telugu Conflicting Evidence Claim ───────────────────────────
    mockVerify.mockResolvedValueOnce(teConflictingResult);

    const textarea3 = screen.getByPlaceholderText(/Paste a news article/i);
    fireEvent.change(textarea3, {
      target: { value: "నగరంలో మెట్రో రైలు సర్వీసులు రేపటి నుంచి నిలిపివేత." },
    });

    const langSelect3 = screen.getByRole("combobox");
    fireEvent.change(langSelect3, { target: { value: "te" } });

    const submitBtn3 = screen.getByRole("button", { name: /Verify Claim/i });
    fireEvent.click(submitBtn3);

    await waitFor(() => {
      const verdict = document.querySelector("h1.verdict-name");
      expect(verdict).toBeInTheDocument();
      expect(verdict).toHaveTextContent(/Conflicting/i);
    });

    // Check evidence cards: one CONTRADICT and one SUPPORT
    expect(screen.getAllByText("Clarification on Metro Operations").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Maintenance Work on Line 1").length).toBeGreaterThan(0);

    // Verify 3 calls were executed with appropriate languages
    expect(mockVerify).toHaveBeenCalledTimes(3);
    expect(mockVerify).toHaveBeenNthCalledWith(
      1,
      "RBI maintains repo rate at 6.5 percent.",
      expect.objectContaining({ language: "auto" })
    );
    expect(mockVerify).toHaveBeenNthCalledWith(
      2,
      "जंगल में अज्ञात उड़नतश्तरी देखी गई।",
      expect.objectContaining({ language: "hi" })
    );
    expect(mockVerify).toHaveBeenNthCalledWith(
      3,
      "నగరంలో మెట్రో రైలు సర్వీసులు రేపటి నుంచి నిలిపివేత.",
      expect.objectContaining({ language: "te" })
    );
  });
});
