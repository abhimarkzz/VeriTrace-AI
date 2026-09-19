import { useState, useId } from "react";

export interface NetworkNode {
  id: string;
  type: "claim" | "source" | "evidence" | "factcheck" | "support" | "contradict" | "context";
  label: string;
  sublabel: string;
  x: number;
  y: number;
  relation?: "SUPPORTS" | "CONTRADICTS" | "CONTEXT" | "INSUFFICIENT";
  details?: string;
}

interface EvidenceNetworkProps {
  claimText?: string;
  evidenceItems?: Array<{
    id: string;
    source: string;
    title: string;
    relation: "SUPPORT" | "CONTRADICT" | "INSUFFICIENT";
  }>;
  onSelectNode?: (node: NetworkNode) => void;
  compact?: boolean;
}

export function EvidenceNetwork({
  claimText = "Reserve Bank of India maintained policy repo rate at 6.5 percent.",
  evidenceItems = [],
  onSelectNode,
  compact = false,
}: EvidenceNetworkProps) {
  const gradientId = useId();
  const [activeNodeId, setActiveNodeId] = useState<string | null>("claim");

  // If real evidence items are passed from a result, map them dynamically;
  // otherwise, present the canonical evidence intelligence topology.
  const nodes: NetworkNode[] = [
    {
      id: "claim",
      type: "claim",
      label: "CENTRAL CLAIM",
      sublabel: claimText.length > 44 ? claimText.slice(0, 44) + "…" : claimText,
      x: 350,
      y: 200,
      details: claimText,
    },
    {
      id: "src-1",
      type: "source",
      label: "SOURCE 01",
      sublabel: evidenceItems[0]?.source || "Official Press Release / Gazette",
      x: 130,
      y: 90,
      relation: "SUPPORTS",
      details: "Official regulatory bulletin announcing monetary policy committee decision.",
    },
    {
      id: "ev-1",
      type: "evidence",
      label: "EVIDENCE",
      sublabel: evidenceItems[0]?.title || "MPC Resolution statement verbatim text",
      x: 130,
      y: 310,
      relation: "SUPPORTS",
      details: "Verbatim extract of the resolution matching policy interest rate figures.",
    },
    {
      id: "fc-1",
      type: "factcheck",
      label: "FACT CHECK",
      sublabel: evidenceItems[1]?.source || "Verified Press Bureau Fact Check",
      x: 570,
      y: 90,
      relation: "SUPPORTS",
      details: "Independent journalistic verification against public records.",
    },
    {
      id: "rel-contradict",
      type: "contradict",
      label: "CROSS-CHECK",
      sublabel: "Contradiction / Misleading Scan",
      x: 570,
      y: 310,
      relation: "CONTRADICTS",
      details: "Checks for conflicting accounts or viral misquotes in public channels.",
    },
    {
      id: "ctx-1",
      type: "context",
      label: "CONTEXT",
      sublabel: "Historical Rate Benchmark",
      x: 350,
      y: 360,
      relation: "CONTEXT",
      details: "Temporal grounding of the claim against prior financial periods.",
    },
  ];

  const activeNode = nodes.find((n) => n.id === activeNodeId) || nodes[0];

  const handleNodeClick = (node: NetworkNode) => {
    setActiveNodeId(node.id);
    onSelectNode?.(node);
  };

  return (
    <div className={`evidence-network-wrapper ${compact ? "evidence-network-compact" : ""}`}>
      <div className="network-header">
        <div className="network-meta">
          <span className="network-pill">TRACEABILITY GRAPH</span>
          <span className="network-hint">Click or hover nodes to trace relationship</span>
        </div>
        <div className="network-active-indicator">
          <span className={`status-dot ${activeNode.type}`} />
          <strong>{activeNode.label}</strong>: {activeNode.sublabel}
        </div>
      </div>

      <div className="svg-container">
        <svg
          viewBox="0 0 700 400"
          className="evidence-network-svg"
          role="img"
          aria-label="Evidence network visualization showing central claim connected to sources, evidence, and verification nodes"
        >
          <defs>
            <linearGradient id={`${gradientId}-line-sup`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.8" />
              <stop offset="100%" stopColor="var(--support)" stopOpacity="0.8" />
            </linearGradient>
            <linearGradient id={`${gradientId}-line-con`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.8" />
              <stop offset="100%" stopColor="var(--contradict)" stopOpacity="0.8" />
            </linearGradient>
            <linearGradient id={`${gradientId}-line-neutral`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="var(--text-faint)" stopOpacity="0.6" />
            </linearGradient>
            <filter id={`${gradientId}-shadow`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.08" />
            </filter>
          </defs>

          {/* Background grid */}
          <g className="network-grid" opacity="0.35">
            <line x1="50" y1="50" x2="650" y2="50" stroke="var(--border)" strokeDasharray="3 3" />
            <line x1="50" y1="200" x2="650" y2="200" stroke="var(--border)" strokeDasharray="3 3" />
            <line x1="50" y1="350" x2="650" y2="350" stroke="var(--border)" strokeDasharray="3 3" />
            <line x1="150" y1="30" x2="150" y2="370" stroke="var(--border)" strokeDasharray="3 3" />
            <line x1="350" y1="30" x2="350" y2="370" stroke="var(--border)" strokeDasharray="3 3" />
            <line x1="550" y1="30" x2="550" y2="370" stroke="var(--border)" strokeDasharray="3 3" />
          </g>

          {/* Connection Lines from Claim to other nodes */}
          {nodes
            .filter((n) => n.id !== "claim")
            .map((target) => {
              const isHighlighted = activeNodeId === "claim" || activeNodeId === target.id;
              const strokeColor =
                target.relation === "SUPPORTS"
                  ? `url(#${gradientId}-line-sup)`
                  : target.relation === "CONTRADICTS"
                  ? `url(#${gradientId}-line-con)`
                  : `url(#${gradientId}-line-neutral)`;

              return (
                <g key={`edge-${target.id}`} className="edge-group">
                  <line
                    x1={350}
                    y1={200}
                    x2={target.x}
                    y2={target.y}
                    stroke={strokeColor}
                    strokeWidth={isHighlighted ? 2.5 : 1.2}
                    strokeDasharray={isHighlighted ? "none" : "4 4"}
                    opacity={isHighlighted ? 1 : 0.4}
                    className="edge-line"
                  />
                  {/* Animated pulse dot */}
                  <circle
                    r={isHighlighted ? 3 : 2}
                    fill={
                      target.relation === "SUPPORTS"
                        ? "var(--support)"
                        : target.relation === "CONTRADICTS"
                        ? "var(--contradict)"
                        : "var(--accent)"
                    }
                    className="edge-pulse"
                  >
                    <animateMotion
                      path={`M350,200 L${target.x},${target.y}`}
                      dur={target.id === "src-1" ? "3s" : target.id === "fc-1" ? "2.5s" : "3.5s"}
                      repeatCount="indefinite"
                    />
                  </circle>
                </g>
              );
            })}

          {/* Nodes */}
          {nodes.map((node) => {
            const isActive = activeNodeId === node.id;
            const isClaim = node.type === "claim";

            return (
              <g
                key={node.id}
                className={`network-node ${node.type} ${isActive ? "active" : ""}`}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => handleNodeClick(node)}
                onMouseEnter={() => setActiveNodeId(node.id)}
                role="button"
                tabIndex={0}
                aria-label={`${node.label}: ${node.sublabel}`}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    handleNodeClick(node);
                  }
                }}
              >
                {/* Node Box */}
                {isClaim ? (
                  <>
                    <rect
                      x="-110"
                      y="-32"
                      width="220"
                      height="64"
                      rx="8"
                      fill="var(--surface)"
                      stroke={isActive ? "var(--accent)" : "var(--border-strong)"}
                      strokeWidth={isActive ? 2.4 : 1.5}
                      filter={`url(#${gradientId}-shadow)`}
                    />
                    <text
                      x="0"
                      y="-8"
                      textAnchor="middle"
                      className="node-label"
                      fill="var(--accent)"
                      fontWeight="700"
                      fontSize="10"
                      letterSpacing="0.08em"
                    >
                      {node.label}
                    </text>
                    <text
                      x="0"
                      y="14"
                      textAnchor="middle"
                      className="node-sublabel"
                      fill="var(--text)"
                      fontSize="11"
                      fontWeight="500"
                    >
                      {node.sublabel}
                    </text>
                  </>
                ) : (
                  <>
                    <rect
                      x="-80"
                      y="-24"
                      width="160"
                      height="48"
                      rx="6"
                      fill="var(--surface)"
                      stroke={
                        node.relation === "SUPPORTS"
                          ? "var(--support)"
                          : node.relation === "CONTRADICTS"
                          ? "var(--contradict)"
                          : isActive
                          ? "var(--accent)"
                          : "var(--border)"
                      }
                      strokeWidth={isActive ? 2 : 1.2}
                      filter={`url(#${gradientId}-shadow)`}
                    />
                    <text
                      x="0"
                      y="-6"
                      textAnchor="middle"
                      className="node-label"
                      fill={
                        node.relation === "SUPPORTS"
                          ? "var(--support)"
                          : node.relation === "CONTRADICTS"
                          ? "var(--contradict)"
                          : "var(--text-muted)"
                      }
                      fontWeight="600"
                      fontSize="9"
                      letterSpacing="0.06em"
                    >
                      {node.label}
                    </text>
                    <text
                      x="0"
                      y="11"
                      textAnchor="middle"
                      className="node-sublabel"
                      fill="var(--text)"
                      fontSize="10"
                      fontWeight="400"
                    >
                      {node.sublabel.length > 20
                        ? node.sublabel.slice(0, 19) + "…"
                        : node.sublabel}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Detail drawer for selected node */}
      {activeNode && (
        <div className="network-detail-strip">
          <div className="strip-title">
            <span className="strip-type-badge">{activeNode.type.toUpperCase()}</span>
            <strong>{activeNode.sublabel}</strong>
          </div>
          <p className="strip-desc">{activeNode.details}</p>
        </div>
      )}
    </div>
  );
}
