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

export type CanvasTheme = "light" | "dark";

export type CanvasPalette = {
  cardFill: string;
  cardStroke: string;
  cardStrokeSelected: string;
  cardStrokeHover: string;
  labelText: string;
  labelMuted: string;
  labelPill: string;
  labelPillStroke: string;
  hierarchyCardFill: string;
  hierarchyBoardFill: string;
  hierarchyBoardFillExpanded: string;
  hierarchyAction: string;
  edgeArrow: string;
  edgeOpacity: number;
  nodeShadow: string;
  dragShadow: string;
};

const lightPalette: CanvasPalette = {
  cardFill: "#ffffff",
  cardStroke: "#d8e0ea",
  cardStrokeSelected: "#6366f1",
  cardStrokeHover: "#a5b4fc",
  labelText: "#172033",
  labelMuted: "#64748b",
  labelPill: "rgba(255,255,255,.96)",
  labelPillStroke: "rgba(99,102,241,.22)",
  hierarchyCardFill: "#ffffff",
  hierarchyBoardFill: "#f8f7ff",
  hierarchyBoardFillExpanded: "#f5f3ff",
  hierarchyAction: "#5969d8",
  edgeArrow: "#9bb0b8",
  edgeOpacity: 0.6,
  nodeShadow: "drop-shadow(0 3px 7px rgba(19, 59, 73, .12))",
  dragShadow: "drop-shadow(0 10px 22px rgba(19, 59, 73, .28))",
};

const darkPalette: CanvasPalette = {
  cardFill: "#202027",
  cardStroke: "rgba(255,255,255,.14)",
  cardStrokeSelected: "#8b93ff",
  cardStrokeHover: "rgba(139,147,255,.65)",
  labelText: "#f2f2f5",
  labelMuted: "#9b9ba7",
  labelPill: "rgba(32,32,39,.92)",
  labelPillStroke: "rgba(255,255,255,.14)",
  hierarchyCardFill: "#202027",
  hierarchyBoardFill: "#24242e",
  hierarchyBoardFillExpanded: "#2a2a3a",
  hierarchyAction: "#a5b4fc",
  edgeArrow: "#8b93a7",
  edgeOpacity: 0.52,
  nodeShadow: "drop-shadow(0 4px 10px rgba(0, 0, 0, .45))",
  dragShadow: "drop-shadow(0 12px 26px rgba(0, 0, 0, .6))",
};

export function canvasPalette(theme: CanvasTheme): CanvasPalette {
  return theme === "dark" ? darkPalette : lightPalette;
}

/** Resolve the canvas theme from the document root, following the app's theme contract. */
export function resolveCanvasTheme(root: { getAttribute(name: string): string | null }): CanvasTheme {
  const explicit = root.getAttribute("data-theme");
  if (explicit === "dark" || explicit === "light") return explicit;
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)")?.matches) {
    return "dark";
  }
  return "light";
}

export type NodeCardMetrics = {
  width: number;
  height: number;
  radius: number;
  accentWidth: number;
};

/**
 * Weave-style node card sizing: a compact rounded card that grows with the label
 * while degree keeps its emphasis through a small size bonus.
 */
export function nodeCardMetrics(label: string, degree: number): NodeCardMetrics {
  const degreeBonus = Math.min(Math.max(degree, 0) * 1.1, 18);
  const width = Math.min(210, Math.max(104, label.length * 6.6 + 34 + degreeBonus));
  return {
    width,
    height: 44,
    radius: 10,
    accentWidth: 4,
  };
}

/** Card width for a node label (truncated like the renderer) with an optional type badge. */
export function nodeCardWidth(label: string, degree: number, typeLabel?: string): number {
  const visible = label.length > 26 ? `${label.slice(0, 26)}…` : label;
  const metrics = nodeCardMetrics(visible, degree);
  return Math.min(210, Math.max(metrics.width, typeLabel ? typeLabel.length * 5.2 + 30 : 0));
}

/**
 * Smooth cubic bezier between two points — the single wire shape used across every
 * layout mode so dragging a node never flips an edge into a different geometry.
 */
export function edgeBezierPath(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  curvature = 0.32,
): string {
  const control = Math.max(28, Math.abs(targetX - sourceX) * curvature);
  return `M ${sourceX} ${sourceY} C ${sourceX + control} ${sourceY}, ${targetX - control} ${targetY}, ${targetX} ${targetY}`;
}

/** Same curve, but exiting the right border of a card and entering the left border. */
export function cardEdgePath(
  sourceX: number,
  sourceY: number,
  sourceWidth: number,
  targetX: number,
  targetY: number,
  targetWidth: number,
  curvature = 0.42,
): string {
  return edgeBezierPath(
    sourceX + sourceWidth / 2,
    sourceY,
    targetX - targetWidth / 2,
    targetY,
    curvature,
  );
}

/** Use the facing borders when the layout does not assign fixed ports. */
export function facingCardEdgePath(
  sourceX: number,
  sourceY: number,
  sourceWidth: number,
  targetX: number,
  targetY: number,
  targetWidth: number,
): string {
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const halfWidths = (sourceWidth + targetWidth) / 2;
  const halfHeight = nodeCardMetrics("", 0).height / 2;
  // Prefer a clear vertical gap over routing through the cards' horizontal overlap.
  if (Math.abs(dx) < halfWidths && Math.abs(dy) >= 2 * halfHeight) {
    const direction = Math.sign(dy);
    const start = sourceY + direction * halfHeight;
    const end = targetY - direction * halfHeight;
    const control = (end - start) / 3;
    return `M ${sourceX} ${start} C ${sourceX} ${start + control}, ${targetX} ${end - control}, ${targetX} ${end}`;
  }
  const direction = dx < 0 ? -1 : 1;
  const start = sourceX + direction * sourceWidth / 2;
  const end = targetX - direction * targetWidth / 2;
  const control = direction * Math.max(0, Math.abs(dx) - halfWidths) * .42;
  return `M ${start} ${sourceY} C ${start + control} ${sourceY}, ${end - control} ${targetY}, ${end} ${targetY}`;
}
