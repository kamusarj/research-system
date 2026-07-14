import type cytoscape from "cytoscape";

export function coseLayout(animate = false): cytoscape.LayoutOptions {
  return {
    name: "cose",
    animate,
    padding: 40,
    fit: true,
    nodeRepulsion: () => 7000,
    idealEdgeLength: () => 90,
  } as cytoscape.LayoutOptions;
}
