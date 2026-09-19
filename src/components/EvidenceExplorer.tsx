import { useState, useMemo } from "react";
import { IconSearch, IconFilter, IconExternal, IconArrow, IconGlobe } from "./Icons";
import { type Language } from "../types";

export interface VerifiedEvidenceEntry {
  id: string;
  claim: string;
  language: Language;
  source: string;
  publisher: string;
  relation: "SUPPORT" | "CONTRADICT" | "INSUFFICIENT";
  date: string;
  snippet: string;
  url: string;
  assessment: "SUPPORTED" | "POTENTIALLY_MISLEADING" | "INSUFFICIENT_EVIDENCE" | "CONFLICTING_EVIDENCE";
}

const VERIFIED_ARCHIVE: VerifiedEvidenceEntry[] = [
  {
    id: "ev-arch-01",
    claim: "Reserve Bank of India maintained policy repo rate at 6.5 percent.",
    language: "en",
    source: "Reserve Bank of India",
    publisher: "Reserve Bank of India (Official Release)",
    relation: "SUPPORT",
    date: "2024-02-08",
    snippet: "The Monetary Policy Committee (MPC) at its meeting decided to keep the policy repo rate under the liquidity adjustment facility (LAF) unchanged at 6.50 per cent.",
    url: "https://www.rbi.org.in",
    assessment: "SUPPORTED",
  },
  {
    id: "ev-arch-02",
    claim: "India has banned UPI payments and digital transactions nationwide.",
    language: "en",
    source: "PIB Fact Check",
    publisher: "Press Information Bureau",
    relation: "CONTRADICT",
    date: "2024-01-15",
    snippet: "A viral message claiming that UPI services will be stopped is completely false. NPCI and RBI have confirmed UPI services continue without interruption.",
    url: "https://factcheck.pib.gov.in",
    assessment: "POTENTIALLY_MISLEADING",
  },
  {
    id: "ev-arch-03",
    claim: "सरकार ने 500 रुपये के सभी पुराने नोट तुरंत बंद करने का आदेश दिया।",
    language: "hi",
    source: "PIB Fact Check Hindi",
    publisher: "Press Information Bureau (Official)",
    relation: "CONTRADICT",
    date: "2023-11-20",
    snippet: "सोशल मीडिया पर वायरल हो रहे इस संदेश में 500 रुपये के नोट बंद होने का दावा पूरी तरह फर्जी है। आरबीआई द्वारा ऐसा कोई सर्कुलर जारी नहीं किया गया है।",
    url: "https://factcheck.pib.gov.in",
    assessment: "POTENTIALLY_MISLEADING",
  },
  {
    id: "ev-arch-04",
    claim: "భారతదేశంలో డిజిటల్ చెల్లింపులు యూపీఐ సేవలు పూర్తిగా రద్దు చేయబడ్డాయి.",
    language: "te",
    source: "Vishwas News Telugu",
    publisher: "Vishwas News",
    relation: "CONTRADICT",
    date: "2024-01-18",
    snippet: "యూపీఐ సేవలు నిలిపివేయబడతాయని సోషల్ మీడియాలో ప్రచారమవుతున్న వార్త అవాస్తవం అని ఎన్‌పీసీఐ స్పష్టం చేసింది. ఈ సందేశాన్ని నమ్మవద్దు.",
    url: "https://www.vishwasnews.com/telugu",
    assessment: "POTENTIALLY_MISLEADING",
  },
  {
    id: "ev-arch-05",
    claim: "World Health Organization recommended RTS,S malaria vaccine for widespread use.",
    language: "en",
    source: "World Health Organization",
    publisher: "WHO News Release",
    relation: "SUPPORT",
    date: "2021-10-06",
    snippet: "WHO is recommending widespread use of the RTS,S/AS01 (RTS,S) malaria vaccine among children in sub-Saharan Africa and in other regions with moderate to high transmission.",
    url: "https://www.who.int",
    assessment: "SUPPORTED",
  },
  {
    id: "ev-arch-06",
    claim: "Chandrayaan-3 successfully touched down on lunar south polar region.",
    language: "en",
    source: "ISRO Mission Directorate",
    publisher: "Indian Space Research Organisation",
    relation: "SUPPORT",
    date: "2023-08-23",
    snippet: "Chandrayaan-3 has achieved soft landing on the Moon. Vikram Lander successfully touched down near 69.37° S, 32.35° E.",
    url: "https://www.isro.gov.in",
    assessment: "SUPPORTED",
  },
];

interface EvidenceExplorerProps {
  onAnalyzeClaim: (claimText: string, lang?: Language) => void;
}

export function EvidenceExplorer({ onAnalyzeClaim }: EvidenceExplorerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLang, setSelectedLang] = useState<string>("all");
  const [selectedAssessment, setSelectedAssessment] = useState<string>("all");
  const [selectedRelation, setSelectedRelation] = useState<string>("all");

  const filteredItems = useMemo(() => {
    return VERIFIED_ARCHIVE.filter((item) => {
      if (selectedLang !== "all" && item.language !== selectedLang) return false;
      if (selectedAssessment !== "all" && item.assessment !== selectedAssessment) return false;
      if (selectedRelation !== "all" && item.relation !== selectedRelation) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesClaim = item.claim.toLowerCase().includes(q);
        const matchesSource = item.publisher.toLowerCase().includes(q);
        const matchesSnippet = item.snippet.toLowerCase().includes(q);
        if (!matchesClaim && !matchesSource && !matchesSnippet) return false;
      }
      return true;
    });
  }, [searchQuery, selectedLang, selectedAssessment, selectedRelation]);

  return (
    <div className="evidence-explorer-view fade-in">
      <header className="explorer-header">
        <span className="editorial-section-tag">AUDITABLE CITATION ARCHIVE</span>
        <h1 className="explorer-title">TRACE THE EVIDENCE</h1>
        <p className="explorer-subtitle">
          Search and cross-examine verified claims, primary sources, and independent fact-check corroborations across English, Hindi, and Telugu.
        </p>
      </header>

      {/* Filter Bar */}
      <div className="card filter-bar-card">
        <div className="search-input-group">
          <IconSearch className="search-icon" />
          <input
            type="search"
            className="explorer-search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search claims, publishers, or evidence snippet keywords…"
            aria-label="Search claims and evidence"
          />
        </div>

        <div className="filters-row">
          <div className="filter-select-wrap">
            <label htmlFor="filter-lang">Language</label>
            <select
              id="filter-lang"
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
            >
              <option value="all">All Languages (EN, HI, TE)</option>
              <option value="en">English (EN)</option>
              <option value="hi">Hindi (HI)</option>
              <option value="te">Telugu (TE)</option>
            </select>
          </div>

          <div className="filter-select-wrap">
            <label htmlFor="filter-assessment">Assessment</label>
            <select
              id="filter-assessment"
              value={selectedAssessment}
              onChange={(e) => setSelectedAssessment(e.target.value)}
            >
              <option value="all">All Outcomes</option>
              <option value="SUPPORTED">Supported</option>
              <option value="POTENTIALLY_MISLEADING">Potentially Misleading</option>
              <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
              <option value="CONFLICTING_EVIDENCE">Conflicting</option>
            </select>
          </div>

          <div className="filter-select-wrap">
            <label htmlFor="filter-rel">Relation</label>
            <select
              id="filter-rel"
              value={selectedRelation}
              onChange={(e) => setSelectedRelation(e.target.value)}
            >
              <option value="all">All Relations</option>
              <option value="SUPPORT">Supports</option>
              <option value="CONTRADICT">Contradicts</option>
              <option value="INSUFFICIENT">Context / Inconclusive</option>
            </select>
          </div>

          {(searchQuery || selectedLang !== "all" || selectedAssessment !== "all" || selectedRelation !== "all") && (
            <button
              className="btn-reset-filters"
              onClick={() => {
                setSearchQuery("");
                setSelectedLang("all");
                setSelectedAssessment("all");
                setSelectedRelation("all");
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Results Count */}
      <div className="results-status-line">
        <span>Showing {filteredItems.length} verified evidence records</span>
      </div>

      {/* Records List */}
      <div className="explorer-grid">
        {filteredItems.map((item) => (
          <div key={item.id} className="explorer-card">
            <div className="card-top-meta">
              <span className={`badge-rel ${item.relation.toLowerCase()}`}>
                {item.relation === "SUPPORT"
                  ? "SUPPORTS"
                  : item.relation === "CONTRADICT"
                  ? "CONTRADICTS"
                  : "CONTEXT"}
              </span>
              <span className="badge-lang">{item.language.toUpperCase()}</span>
              <span className="entry-date">{item.date}</span>
            </div>

            <h3 className="entry-claim">&ldquo;{item.claim}&rdquo;</h3>

            <div className="entry-snippet-box">
              <span className="source-label">{item.publisher}</span>
              <p className="snippet-text">&ldquo;{item.snippet}&rdquo;</p>
            </div>

            <div className="card-bottom-actions">
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="btn-open-source"
              >
                <span>Visit Source</span>
                <IconExternal className="icon-sm" />
              </a>

              <button
                className="btn-run-claim"
                onClick={() => onAnalyzeClaim(item.claim, item.language)}
              >
                <span>Verify in Analyzer</span>
                <IconArrow className="icon-sm" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredItems.length === 0 && (
        <div className="card empty-explorer-state">
          <h3>No matching evidence found</h3>
          <p>Try adjusting your search keywords or clearing language and assessment filters.</p>
        </div>
      )}
    </div>
  );
}
