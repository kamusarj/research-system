"use client";

import { useMemo } from "react";
import type { DocumentGraph, DocumentGraphNode } from "@/lib/types";

type PositionedNode = DocumentGraphNode & { x: number; y: number };

const CANVAS_WIDTH = 1040;
const MAX_COLUMNS = 5;
const NODE_ROW_HEIGHT = 96;
const LAYER_GAP = 64;
const TOP_PADDING = 70;

export function DocumentGraphCanvas({
  graph,
  selectedId,
  onSelect,
}: {
  graph: DocumentGraph;
  selectedId: string | null;
  onSelect: (node: DocumentGraphNode) => void;
}) {
  const layout = useMemo(() => {
    const byId = new Map(graph.nodes.map((node) => [node.id, node]));
    const depth = (node: DocumentGraphNode, seen = new Set<string>()): number => {
      if (!node.parent_node_id || seen.has(node.id)) return 0;
      const parent = byId.get(node.parent_node_id);
      if (!parent) return 0;
      seen.add(node.id);
      return 1 + depth(parent, seen);
    };
    const layers = new Map<number, DocumentGraphNode[]>();
    for (const node of graph.nodes) {
      const level = depth(node);
      layers.set(level, [...(layers.get(level) ?? []), node]);
    }
    const width = CANVAS_WIDTH;
    const positioned: PositionedNode[] = [];
    let layerTop = TOP_PADDING;
    for (const [, nodes] of [...layers.entries()].sort(([a], [b]) => a - b)) {
      const ordered = [...nodes].sort((left, right) => {
        const leftParent = byId.get(left.parent_node_id ?? "")?.label ?? "";
        const rightParent = byId.get(right.parent_node_id ?? "")?.label ?? "";
        return (
          leftParent.localeCompare(rightParent) ||
          left.node_type.localeCompare(right.node_type) ||
          left.label.localeCompare(right.label)
        );
      });
      const columns = Math.min(MAX_COLUMNS, ordered.length);
      const rows = Math.ceil(ordered.length / MAX_COLUMNS);
      ordered.forEach((node, index) => {
        const column = index % MAX_COLUMNS;
        const row = Math.floor(index / MAX_COLUMNS);
        positioned.push({
          ...node,
          x: ((column + 1) * width) / (columns + 1),
          y: layerTop + row * NODE_ROW_HEIGHT,
        });
      });
      layerTop += rows * NODE_ROW_HEIGHT + LAYER_GAP;
    }
    const height = Math.max(460, layerTop - LAYER_GAP + 70);
    return { nodes: positioned, width, height };
  }, [graph.nodes]);
  const byId = new Map(layout.nodes.map((node) => [node.id, node]));
  const links = [
    ...layout.nodes
      .filter((node) => node.parent_node_id)
      .map((node) => ({
        id: `parent-${node.id}`,
        source: byId.get(node.parent_node_id ?? ""),
        target: node,
        kind: "contains",
      })),
    ...graph.edges.map((edge) => ({
      id: edge.id,
      source: byId.get(edge.source_node_id),
      target: byId.get(edge.target_node_id),
      kind: edge.edge_type,
    })),
  ].filter((link) => link.source && link.target);

  return (
    <div className="document-graph-canvas" data-testid="document-graph-canvas">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="img"
        aria-label="Đồ thị tài liệu"
        style={{ width: `${layout.width}px`, minWidth: "100%" }}
      >
        <g className="document-graph-links">
          {links.map((link) => (
            <line
              key={link.id}
              x1={link.source?.x}
              y1={(link.source?.y ?? 0) + 25}
              x2={link.target?.x}
              y2={(link.target?.y ?? 0) - 25}
              className={link.kind === "contains" ? "structural" : "semantic"}
            />
          ))}
        </g>
        <g className="document-graph-nodes">
          {layout.nodes.map((node) => (
            <g
              key={node.id}
              className={`document-graph-node ${selectedId === node.id ? "selected" : ""} ${node.evidence_status}`}
              transform={`translate(${node.x}, ${node.y})`}
              role="button"
              tabIndex={0}
              aria-label={node.label}
              onClick={() => onSelect(graph.nodes.find((item) => item.id === node.id) ?? node)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  onSelect(graph.nodes.find((item) => item.id === node.id) ?? node);
                }
              }}
            >
              <rect x="-82" y="-26" width="164" height="52" rx="12" />
              <text className="node-label" textAnchor="middle" y="-2">
                {node.label.length > 25 ? `${node.label.slice(0, 24)}…` : node.label}
              </text>
              <text className="node-type" textAnchor="middle" y="15">{node.node_type}</text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
