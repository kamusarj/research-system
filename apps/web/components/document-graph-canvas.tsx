"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { DocumentGraph, DocumentGraphNode } from "@/lib/types";

type PositionedNode = DocumentGraphNode & { x: number; y: number };
type Point = { x: number; y: number };
type NodeDrag = {
  id: string;
  pointerId: number;
  element: SVGGElement;
  start: Point;
  origin: Point;
  moved: boolean;
};

const CANVAS_WIDTH = 1040;
const MAX_COLUMNS = 5;
const NODE_ROW_HEIGHT = 96;
const LAYER_GAP = 64;
const TOP_PADDING = 70;
const DRAG_THRESHOLD = 2;
const CARD_HALF_WIDTH = 82;
const CARD_HALF_HEIGHT = 26;
const CARD_INSET = 2;

function keepCardInCanvas(point: Point, width: number, height: number): Point {
  const insetX = CARD_HALF_WIDTH + CARD_INSET;
  const insetY = CARD_HALF_HEIGHT + CARD_INSET;
  return {
    x: Math.min(Math.max(point.x, insetX), width - insetX),
    y: Math.min(Math.max(point.y, insetY), height - insetY),
  };
}

function verticalBezier(source: Point, target: Point): string {
  const control = Math.max(28, Math.abs(target.y - source.y) * 0.45);
  return `M ${source.x} ${source.y} C ${source.x} ${source.y + control}, ${target.x} ${target.y - control}, ${target.x} ${target.y}`;
}

function horizontalBezier(source: Point, target: Point): string {
  const control = Math.max(28, Math.abs(target.x - source.x) * 0.32);
  return `M ${source.x} ${source.y} C ${source.x + control} ${source.y}, ${target.x - control} ${target.y}, ${target.x} ${target.y}`;
}

const schedule =
  typeof requestAnimationFrame === "function"
    ? (callback: () => void) => requestAnimationFrame(() => callback())
    : (callback: () => void) => setTimeout(callback, 16);

const cancelSchedule =
  typeof cancelAnimationFrame === "function"
    ? (handle: number) => cancelAnimationFrame(handle)
    : (handle: number) => clearTimeout(handle);

export function DocumentGraphCanvas({
  graph,
  selectedId,
  onSelect,
  rearrangeLabel = "Sắp xếp lại",
}: {
  graph: DocumentGraph;
  selectedId: string | null;
  onSelect: (node: DocumentGraphNode) => void;
  rearrangeLabel?: string;
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

  const [offsets, setOffsets] = useState<Record<string, Point>>({});
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<NodeDrag | null>(null);
  const frameRef = useRef<number | null>(null);
  const pendingRef = useRef<{ id: string; point: Point } | null>(null);
  const suppressClickRef = useRef<string | null>(null);

  const clearPending = useCallback(() => {
    if (frameRef.current !== null) cancelSchedule(frameRef.current);
    frameRef.current = null;
    pendingRef.current = null;
  }, []);

  useEffect(() => clearPending, [clearPending]);

  const toSvgPoint = useCallback((clientX: number, clientY: number): Point => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const matrix = svg.getScreenCTM?.();
    if (matrix && typeof DOMPoint !== "undefined") {
      return new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse());
    }
    const rect = svg.getBoundingClientRect();
    const scale = rect.width / CANVAS_WIDTH || 1;
    return { x: (clientX - rect.left) / scale, y: (clientY - rect.top) / scale };
  }, []);

  const positionOf = useCallback(
    (node: PositionedNode): Point => keepCardInCanvas(offsets[node.id] ?? node, layout.width, layout.height),
    [offsets, layout.width, layout.height],
  );

  const handlePointerDown = useCallback((event: React.PointerEvent<SVGGElement>, node: PositionedNode) => {
    if ((typeof event.button === "number" && event.button !== 0) || dragRef.current) return;
    suppressClickRef.current = null;
    dragRef.current = {
      id: node.id,
      pointerId: event.pointerId,
      element: event.currentTarget,
      start: toSvgPoint(event.clientX, event.clientY),
      origin: positionOf(node),
      moved: false,
    };
    try {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } catch {
      // Pointer capture is a nicety (jsdom and older engines may reject it).
    }
  }, [positionOf, toSvgPoint]);

  const handlePointerMove = useCallback((event: React.PointerEvent<SVGGElement>, node: PositionedNode) => {
    const drag = dragRef.current;
    if (!drag || drag.id !== node.id || drag.pointerId !== event.pointerId) return;
    const point = toSvgPoint(event.clientX, event.clientY);
    const dx = point.x - drag.start.x;
    const dy = point.y - drag.start.y;
    if (!drag.moved) {
      if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      drag.moved = true;
      event.currentTarget.classList.add("dragging");
    }
    pendingRef.current = {
      id: node.id,
      point: keepCardInCanvas({ x: drag.origin.x + dx, y: drag.origin.y + dy }, layout.width, layout.height),
    };
    if (frameRef.current === null) {
      frameRef.current = schedule(() => {
        frameRef.current = null;
        const pending = pendingRef.current;
        pendingRef.current = null;
        if (pending) setOffsets((previousOffsets) => ({ ...previousOffsets, [pending.id]: pending.point }));
      }) as unknown as number;
    }
  }, [layout.width, layout.height, toSvgPoint]);

  const endDrag = useCallback((drag: NodeDrag) => {
    dragRef.current = null;
    drag.element.classList.remove("dragging");
    try {
      drag.element.releasePointerCapture?.(drag.pointerId);
    } catch {
      // Same tolerance as setPointerCapture.
    }
  }, []);

  useLayoutEffect(() => {
    const nodeIds = new Set(graph.nodes.map((node) => node.id));
    const drag = dragRef.current;
    if (drag && (!nodeIds.has(drag.id) || !drag.element.isConnected)) {
      clearPending();
      endDrag(drag);
    }
    if (suppressClickRef.current && !nodeIds.has(suppressClickRef.current)) {
      suppressClickRef.current = null;
    }
    setOffsets((current) => {
      const entries = Object.entries(current);
      const retained = entries.filter(([nodeId]) => nodeIds.has(nodeId));
      return retained.length === entries.length ? current : Object.fromEntries(retained);
    });
  }, [graph.nodes, clearPending, endDrag]);

  const handlePointerEnd = useCallback((event: React.PointerEvent<SVGGElement>, cancelled: boolean) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId || drag.element !== event.currentTarget) return;
    const pending = pendingRef.current;
    clearPending();
    endDrag(drag);
    suppressClickRef.current = !cancelled && drag.moved ? drag.id : null;
    const position = cancelled ? drag.origin : pending?.point;
    if (drag.moved && position) {
      setOffsets((current) => ({ ...current, [drag.id]: position }));
    }
  }, [clearPending, endDrag]);

  const rearrange = () => {
    if (dragRef.current) endDrag(dragRef.current);
    clearPending();
    suppressClickRef.current = null;
    setOffsets({});
  };

  const resolved = layout.nodes.map((node) => ({ ...node, ...positionOf(node) }));
  const resolvedById = new Map(resolved.map((node) => [node.id, node]));
  const links = [
    ...layout.nodes
      .filter((node) => node.parent_node_id)
      .map((node) => ({
        id: `parent-${node.id}`,
        source: resolvedById.get(node.parent_node_id ?? ""),
        target: resolvedById.get(node.id),
        kind: "contains",
      })),
    ...graph.edges.map((edge) => ({
      id: edge.id,
      source: resolvedById.get(edge.source_node_id),
      target: resolvedById.get(edge.target_node_id),
      kind: edge.edge_type,
    })),
  ].filter((link) => link.source && link.target);

  return (
    <div className="document-graph-viewport">
      <button type="button" className="document-graph-rearrange secondary" onClick={rearrange}>
        {rearrangeLabel}
      </button>
      <div className="document-graph-canvas" data-testid="document-graph-canvas">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label="Đồ thị tài liệu"
          style={{ width: `${layout.width}px`, minWidth: "100%" }}
        >
          <g className="document-graph-links">
            {links.map((link) => (
              <path
                key={link.id}
                d={link.kind === "contains"
                  ? verticalBezier(link.source!, link.target!)
                  : horizontalBezier(link.source!, link.target!)}
                className={link.kind === "contains" ? "structural" : "semantic"}
              />
            ))}
          </g>
          <g className="document-graph-nodes">
            {resolved.map((node) => (
              <g
                key={node.id}
                className={`document-graph-node ${selectedId === node.id ? "selected" : ""} ${node.evidence_status}`}
                transform={`translate(${node.x}, ${node.y})`}
                role="button"
                tabIndex={0}
                aria-label={node.label}
                onPointerDown={(event) => handlePointerDown(event, node)}
                onPointerMove={(event) => handlePointerMove(event, node)}
                onPointerUp={(event) => handlePointerEnd(event, false)}
                onPointerCancel={(event) => handlePointerEnd(event, true)}
                onLostPointerCapture={(event) => handlePointerEnd(event, true)}
                onClick={() => {
                  if (suppressClickRef.current === node.id) {
                    suppressClickRef.current = null;
                    return;
                  }
                  onSelect(graph.nodes.find((item) => item.id === node.id) ?? node);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(graph.nodes.find((item) => item.id === node.id) ?? node);
                  }
                }}
              >
                <rect x={-CARD_HALF_WIDTH} y={-CARD_HALF_HEIGHT}
                  width={CARD_HALF_WIDTH * 2} height={CARD_HALF_HEIGHT * 2} rx="10" />
                <rect className="node-accent" x="-81" y="-25" width="4" height="50" rx="2" />
                <text className="node-label" textAnchor="middle" y="-2">
                  {node.label.length > 25 ? `${node.label.slice(0, 24)}…` : node.label}
                </text>
                <text className="node-type" textAnchor="middle" y="15">{node.node_type}</text>
              </g>
            ))}
          </g>
        </svg>
      </div>
    </div>
  );
}
