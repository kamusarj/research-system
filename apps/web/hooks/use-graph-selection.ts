"use client";

import { useState } from "react";
import type { GraphEdge, GraphNode, GraphSelection } from "@/lib/knowledge-graph/types";

export function useGraphSelection() {
  const [selection, setSelection] = useState<GraphSelection>(null);
  return {
    selection,
    selectNode: (node: GraphNode) => setSelection({ kind: "node", value: node }),
    selectEdge: (edge: GraphEdge) => setSelection({ kind: "edge", value: edge }),
    clearSelection: () => setSelection(null),
  };
}
