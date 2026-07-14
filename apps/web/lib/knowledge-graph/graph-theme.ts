import type cytoscape from "cytoscape";

export const graphColors: Record<string, string> = {
  Source: "#65a9ff",
  ResearchItem: "#6ee7c7",
  Repository: "#a78bfa",
  Article: "#79d99f",
  Reel: "#e985a4",
  PDF: "#e9a66f",
  Concept: "#65a9ff",
  Technology: "#73e2c2",
  AgentPattern: "#b8a4ff",
  BusinessDomain: "#e8d58a",
  Person: "#70d7e8",
  CollectorSource: "#67c7a1",
  ResearchGap: "#ef8795",
  Claim: "#dce8f8",
};

export const fallbackGraphColor = "#94a3b8";

export const graphStyles = [
  {
    selector: "node",
    style: {
      "background-color": fallbackGraphColor,
      label: "data(label)",
      color: "#dce8f8",
      "font-size": 10,
      "text-wrap": "ellipsis",
      "text-max-width": 110,
      "text-valign": "bottom",
      "text-margin-y": 8,
      width: 36,
      height: 36,
      "border-width": 2,
      "border-color": "#081321",
    },
  },
  {
    selector: "node[type = 'ResearchItem']",
    style: { shape: "round-rectangle", width: 44, height: 34 },
  },
  { selector: "node.zoomed-out", style: { label: "" } },
  {
    selector: "edge",
    style: {
      width: 1.2,
      "line-color": "#304968",
      "target-arrow-color": "#54708f",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      opacity: 0.55,
      label: "",
    },
  },
  { selector: "edge[type = 'SUPPORTS']", style: { "line-color": "#55bfa0" } },
  {
    selector: "edge[type = 'CONTRADICTS']",
    style: { "line-color": "#d66f82", "line-style": "dashed" },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#ffffff",
      "border-width": 4,
      "shadow-color": "#6ee7c7",
      "shadow-blur": 18,
      "shadow-opacity": 0.8,
    },
  },
  {
    selector: "edge:selected",
    style: { width: 3, opacity: 1, label: "data(type)", color: "#dce8f8", "font-size": 9 },
  },
  ...Object.entries(graphColors).map(([type, color]) => ({
    selector: `node[type = '${type}']`,
    style: { "background-color": color },
  })),
] as unknown as cytoscape.StylesheetCSS[];
