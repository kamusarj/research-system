export const nodeColors: Record<string, string> = {
  SystemRoot: "#38bdf8",
  SystemPillar: "#818cf8",
  Source: "#60a5fa",
  ResearchItem: "#22d3ee",
  Repository: "#4ade80",
  Article: "#34d399",
  Reel: "#fb7185",
  PDF: "#c084fc",
  Concept: "#a78bfa",
  Technology: "#2dd4bf",
  AgentPattern: "#818cf8",
  BusinessDomain: "#fbbf24",
  Person: "#94a3b8",
  CollectorSource: "#60a5fa",
  ResearchGap: "#fb7185",
  EvidenceClaim: "#f472b6",
  Finding: "#4ade80",
  Limitation: "#fb7185",
  Metric: "#fbbf24",
  Claim: "#f472b6",
};

export const fallbackNodeColor = "#94a3b8";

export const edgeColors: Record<string, string> = {
  SUPPORTS: "#3dba8a",
  CONTRADICTS: "#e85d75",
  RESEARCHES: "#818cf8",
  USES_TECH: "#2dd4bf",
  COLLECTED_FROM: "#60a5fa",
  RELATED_TO: "#c084fc",
  APPLIES_TO: "#fbbf24",
  IMPLEMENTS_PATTERN: "#a78bfa",
  AUTHORED_BY: "#94a3b8",
  REVIEWS: "#fb7185",
};

export const fallbackEdgeColor = "#64748b";

export const nodeShapes: Record<string, "circle" | "rect" | "diamond"> = {
  SystemRoot: "rect",
  SystemPillar: "rect",
  ResearchItem: "rect",
  Concept: "circle",
  Technology: "diamond",
};

export function getNodeColor(type: string): string {
  return nodeColors[type] ?? fallbackNodeColor;
}

export function getEdgeColor(type: string): string {
  return edgeColors[type] ?? fallbackEdgeColor;
}

export function getNodeShape(type: string): "circle" | "rect" | "diamond" {
  return nodeShapes[type] ?? "circle";
}

export function getNodeRadius(type: string, degree: number): number {
  const baseRadius = type === "SystemRoot" ? 15 : type === "SystemPillar" ? 13 : type === "ResearchItem" ? 11 : 8;
  const degreeBonus = Math.min(degree * .9, 7);
  return baseRadius + degreeBonus;
}

export function getEdgeWidth(type: string): number {
  return type === "CONTRADICTS" ? 2 : 1.5;
}

export function getEdgeDash(type: string): string {
  return type === "CONTRADICTS" ? "6,3" : "";
}
