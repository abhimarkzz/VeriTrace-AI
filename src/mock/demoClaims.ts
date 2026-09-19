/**
 * Curated demo scenarios.
 *
 * Every source below is a real, resolvable article and every snippet is copied
 * verbatim from it. Nothing here is invented, and no quote is attributed to an
 * organisation that did not publish it — a tool about misinformation cannot
 * demo itself on fabricated citations. The numeric scores are illustrative.
 */

import type { EvidenceItem, Language, VerificationResult } from "../types";

const ENTRACKR: EvidenceItem = {
  id: "entrackr-aug-2026",
  title: "UPI hits new record with 24.51 Bn transactions in August",
  source: "Entrackr",
  url: "https://entrackr.com/news/upi-hits-new-record-with-2451-bn-transactions-in-august-12478578",
  snippet:
    "Unified Payments Interface (UPI) posted its highest ever monthly transaction volume in August 2026, with 24.51 billion transactions worth Rs 29.82 lakh crore, according to data released by the National Payments Corporation of India (NPCI).",
  relevanceScore: 0.94,
  sourceQuality: 0.82,
  relation: "CONTRADICT",
};

const MEDIANAMA: EvidenceItem = {
  id: "medianama-aug-2026",
  title:
    "UPI hits record 24.51 billion transactions in August, but growth uneven across digital payment rails",
  source: "MediaNama",
  url: "https://www.medianama.com/2026/09/223-upi-transactions-august-2026/",
  snippet:
    "India's Unified Payments Interface (UPI) processed 24.51 billion transactions worth Rs 29.82 lakh crore in August 2026, marking its highest monthly transaction volume to date, according to the National Payments Corporation of India (NPCI).",
  relevanceScore: 0.91,
  sourceQuality: 0.85,
  relation: "CONTRADICT",
};

const SMESTREET: EvidenceItem = {
  id: "smestreet-gff-2026",
  title: "RBI Governor Launches New UPI Innovations at GFF 2026",
  source: "SMEStreet",
  url: "https://smestreet.in/banking/rbi-governor-launches-new-upi-innovations-at-gff-2026-12524420",
  snippet:
    "The Reserve Bank of India (RBI) Governor, Shri Sanjay Malhotra, announced the launch of two customer-centric UPI innovations at the Global Fintech Fest (GFF) 2026.",
  relevanceScore: 0.79,
  sourceQuality: 0.74,
  relation: "CONTRADICT",
};

const TAXGURU_PIB: EvidenceItem = {
  id: "taxguru-pib-upi",
  title: "UPI Reaches 11 Countries as India's Digital Payments Ecosystem Expands",
  source: "TaxGuru (reproducing a PIB release)",
  url: "https://taxguru.in/finance/upi-reaches-11-countries-indias-digital-payments-ecosystem-expands.html",
  snippet:
    "The Unified Payments Interface (UPI), developed by the National Payments Corporation of India (NPCI), has emerged as a cornerstone of India's digital payments revolution.",
  relevanceScore: 0.83,
  sourceQuality: 0.88,
  relation: "SUPPORT",
};

const DECCAN_MDR: EvidenceItem = {
  id: "deccan-mdr",
  title: "UPI Payments Above ₹2,000 to Attract 0.4% MDR: NPCI",
  source: "Deccan Chronicle",
  url: "https://www.deccanchronicle.com/business/upi-charges-loom-banks-panel-to-decide-on-merchant-fees-for-transactions-above-2000-1987584",
  snippet:
    "the committee would soon take decision on Merchant Discount Rate (MDR) on UPI transaction above Rs 2,000 based on various factors including self-sustainability and market expansion.",
  relevanceScore: 0.68,
  sourceQuality: 0.79,
  relation: "INSUFFICIENT",
};

const AAJTAK: EvidenceItem = {
  id: "aajtak-aug-2026",
  title: "UPI का नया रिकॉर्ड... अगस्‍त में 24.5 अरब ट्रांजेक्‍शन, 11 देशों तक फैला नेटवर्क!",
  source: "Aaj Tak",
  url: "https://www.aajtak.in/business/news/story/upi-payments-transaction-record-high-in-august-why-digital-payments-rise-rapidly-tutd-dskc-2634075-2026-09-01",
  snippet:
    "अगस्त का आंकड़ा पिछले साल अगस्त में दर्ज किए गए 19.63 बिलियन लेनदेन से 22% अधिक था.",
  relevanceScore: 0.93,
  sourceQuality: 0.83,
  relation: "SUPPORT",
};

const EENADU: EvidenceItem = {
  id: "eenadu-aug-2026",
  title: "రికార్డు స్థాయికి చేరువలో యూపీఐ లావాదేవీలు",
  source: "Eenadu",
  url: "https://www.eenadu.net/telugu-news/business/general/0199/126157627",
  snippet:
    "ఆగస్టులో యూనిఫైడ్‌ పేమెంట్స్‌ ఇంటర్‌ఫేస్‌ (యూపీఐ) ద్వారా జరిగిన లావాదేవీల విలువ రూ.29.8 లక్షల కోట్లుగా నమోదైందని నేషనల్‌ పేమెంట్స్‌ కార్పొరేషన్‌ ఆఫ్‌ ఇండియా (ఎన్‌పీసీఐ) వెల్లడించింది.",
  relevanceScore: 0.92,
  sourceQuality: 0.84,
  relation: "SUPPORT",
};

const ONEINDIA_MDR: EvidenceItem = {
  id: "oneindia-mdr",
  title: "UPI Is NOT Entirely Free: Government Ends Zero-MDR Model For Big Payments",
  source: "Oneindia",
  url: "https://www.oneindia.com/india/upi-is-not-entirely-free-government-ends-zero-mdr-model-for-big-payments-oneindia-ground-report-8206461.html",
  snippet:
    "From October 15, 2026, merchant UPI transactions above Rs 2000 will attract a 0.4% Merchant Discount Rate (MDR) under the new framework.",
  relevanceScore: 0.9,
  sourceQuality: 0.76,
  relation: "CONTRADICT",
};

const SCC_MDR: EvidenceItem = {
  id: "scc-mdr-faq",
  title:
    "UPI MDR explained: No charges for consumers, 0.4% fee on select merchant transactions above ₹2,000",
  source: "SCC Online",
  url: "https://www.scconline.com/blog/post/2026/09/16/npci-released-upi-mdr-faqs-explained/",
  snippet:
    "Consumers will not have to pay any fee for scanning UPI QR codes at local shops, street vendors or other merchants, regardless of the transaction value.",
  relevanceScore: 0.93,
  sourceQuality: 0.86,
  relation: "SUPPORT",
};

const FINMIN_CLARIFICATION: EvidenceItem = {
  id: "finmin-upi-free",
  title:
    "Ministry of Finance Clarification: UPI Continues to Remain Free for Peer to Peer Transactions and 96% of Merchant Transactions",
  source: "GovtEmployeesHub (reproducing a Ministry of Finance release)",
  url: "https://www.govtemployeeshub.com/2026/09/ministry-of-finance-clarification-upi.html",
  snippet: "All person-to-person (P2P) UPI transactions will remain completely free",
  relevanceScore: 0.88,
  sourceQuality: 0.81,
  relation: "SUPPORT",
};

const supporting = (item: EvidenceItem): EvidenceItem => ({ ...item, relation: "SUPPORT" });
const contradicting = (item: EvidenceItem): EvidenceItem => ({
  ...item,
  relation: "CONTRADICT",
});
const inconclusive = (item: EvidenceItem): EvidenceItem => ({
  ...item,
  relation: "INSUFFICIENT",
});

export interface Scenario {
  id: string;
  label: string;
  language: Language;
  matchKeywords: string[];
  result: VerificationResult;
}

export const SCENARIOS: Scenario[] = [
  {
    id: "upi-ban-en",
    label: "Contradicted claim",
    language: "en",
    matchKeywords: ["upi", "banned", "shut down"],
    result: {
      claim: "India has banned UPI payments and the service has been shut down nationwide.",
      language: "en",
      claimType: "Factual claim",
      assessment: "POTENTIALLY_MISLEADING",
      confidence: 0.86,
      confidenceBreakdown: {
        evidenceAgreement: 0.92,
        evidenceRelevance: 0.88,
        sourceQuality: 0.8,
        modelConfidence: 0.79,
      },
      evidenceStrength: "STRONG",
      explanation:
        "Every source traced for this claim reports UPI operating normally, including record monthly transaction volumes for August 2026 and newly launched UPI features from the Reserve Bank of India. Nothing retrieved indicates a nationwide shutdown, so the claim is contradicted by the strongest available evidence.",
      evidence: [ENTRACKR, MEDIANAMA, SMESTREET],
    },
  },
  {
    id: "upi-record-en",
    label: "Supported claim",
    language: "en",
    matchKeywords: ["upi", "24.51", "record", "billion"],
    result: {
      claim:
        "UPI, developed by the National Payments Corporation of India, processed a record 24.51 billion transactions worth Rs 29.82 lakh crore in August 2026.",
      language: "en",
      claimType: "Statistical claim",
      assessment: "SUPPORTED",
      confidence: 0.89,
      confidenceBreakdown: {
        evidenceAgreement: 0.95,
        evidenceRelevance: 0.9,
        sourceQuality: 0.85,
        modelConfidence: 0.81,
      },
      evidenceStrength: "STRONG",
      explanation:
        "Multiple independent outlets report the same figure — 24.51 billion transactions worth Rs 29.82 lakh crore in August 2026 — each attributing it to NPCI. The transaction count, the value and the attribution to NPCI are all corroborated.",
      evidence: [supporting(ENTRACKR), supporting(MEDIANAMA), TAXGURU_PIB],
    },
  },
  {
    id: "upi-cap-en",
    label: "Insufficient evidence",
    language: "en",
    matchKeywords: ["cap", "20 transactions", "per day", "upi"],
    result: {
      claim: "The RBI will cap UPI users at 20 transactions per day starting April 2027.",
      language: "en",
      claimType: "Policy claim",
      assessment: "INSUFFICIENT_EVIDENCE",
      confidence: 0.34,
      confidenceBreakdown: {
        evidenceAgreement: 0.18,
        evidenceRelevance: 0.55,
        sourceQuality: 0.76,
        modelConfidence: 0.41,
      },
      evidenceStrength: "WEAK",
      explanation:
        "Sources discussing UPI policy were found, but none of them mention a daily transaction cap of any size. Related coverage of UPI rule changes does not establish this specific claim, and absence of evidence is not evidence that the claim is false — it simply cannot be assessed from what was retrieved.",
      evidence: [inconclusive(SMESTREET), DECCAN_MDR],
    },
  },
  {
    id: "upi-free-en",
    label: "Conflicting evidence",
    language: "en",
    matchKeywords: ["upi", "free", "charge"],
    result: {
      claim: "UPI payments in India are free of charge.",
      language: "en",
      claimType: "Policy claim",
      assessment: "CONFLICTING_EVIDENCE",
      confidence: 0.57,
      confidenceBreakdown: {
        evidenceAgreement: 0.34,
        evidenceRelevance: 0.9,
        sourceQuality: 0.81,
        modelConfidence: 0.62,
      },
      evidenceStrength: "MODERATE",
      explanation:
        "Sources genuinely disagree, because the claim is ambiguous about who is being charged. A 0.4% merchant fee applies to UPI payments above Rs 2,000 from October 2026, which some outlets report as UPI no longer being free. Other sources, including a Ministry of Finance clarification, state that consumers pay nothing and that person-to-person transfers remain free. Both descriptions are accurate about different parts of the same policy, so a single verdict would misrepresent the evidence.",
      evidence: [SCC_MDR, ONEINDIA_MDR, FINMIN_CLARIFICATION, contradicting(DECCAN_MDR)],
    },
  },
  {
    id: "upi-record-hi",
    label: "Hindi example",
    language: "hi",
    matchKeywords: ["upi", "अरब", "लेनदेन"],
    result: {
      claim: "अगस्त 2026 में UPI से 24.5 अरब से ज्यादा लेनदेन हुए।",
      language: "hi",
      claimType: "Statistical claim",
      assessment: "SUPPORTED",
      confidence: 0.85,
      confidenceBreakdown: {
        evidenceAgreement: 0.93,
        evidenceRelevance: 0.89,
        sourceQuality: 0.82,
        modelConfidence: 0.74,
      },
      evidenceStrength: "STRONG",
      explanation:
        "Hindi-language reporting confirms the August 2026 figure and notes it is 22% higher than the same month a year earlier. English-language coverage of the same NPCI data independently corroborates the number, so the claim holds across both languages.",
      evidence: [AAJTAK, supporting(ENTRACKR)],
    },
  },
  {
    id: "upi-record-te",
    label: "Telugu example",
    language: "te",
    matchKeywords: ["యూపీఐ", "లావాదేవీ", "లక్షల"],
    result: {
      claim: "ఆగస్టు 2026లో యూపీఐ లావాదేవీల విలువ రూ.29.8 లక్షల కోట్లు.",
      language: "te",
      claimType: "Statistical claim",
      assessment: "SUPPORTED",
      confidence: 0.84,
      confidenceBreakdown: {
        evidenceAgreement: 0.92,
        evidenceRelevance: 0.88,
        sourceQuality: 0.83,
        modelConfidence: 0.72,
      },
      evidenceStrength: "STRONG",
      explanation:
        "Telugu-language reporting attributes the Rs 29.8 lakh crore August figure directly to NPCI, and English-language coverage of the same data reports the same value. The claim is supported by sources in two languages.",
      evidence: [EENADU, supporting(MEDIANAMA)],
    },
  },
];

export const DEMO_PROMPTS = SCENARIOS.map((scenario) => ({
  id: scenario.id,
  label: scenario.label,
  language: scenario.language,
  text: scenario.result.claim,
}));

/** Shown for input that matches no prepared scenario. */
export const UNKNOWN_CLAIM_RESULT: VerificationResult = {
  claim: "",
  language: "en",
  claimType: "Unrecognised input",
  assessment: "INSUFFICIENT_EVIDENCE",
  confidence: 0.12,
  confidenceBreakdown: {
    evidenceAgreement: 0,
    evidenceRelevance: 0,
    sourceQuality: 0,
    modelConfidence: 0.12,
  },
  evidenceStrength: "WEAK",
  explanation:
    "This prototype runs on a prepared set of demonstration claims and did not find a match for this input, so no evidence trail could be built. Try one of the demo claims to see the full workflow.",
  evidence: [],
};
