"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { D3GraphRenderer } from "@/lib/knowledge-graph/d3-graph-renderer";
import type { GraphEdge, GraphLayoutMode, GraphNode } from "@/lib/knowledge-graph/types";

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layoutNonce: number;
  fitNonce: number;
  layout: GraphLayoutMode;
  labelsVisible: boolean;
  onNodeSelect: (node: GraphNode) => void;
  onEdgeSelect: (edge: GraphEdge) => void;
  onClearSelection: () => void;
  onExpandNode: (nodeId: string) => void;
  hierarchyLabels?: {
    board: string;
    nodes: string;
    open: string;
    close: string;
  };
  status?: {
    nodes: string;
    edges: string;
    detail: string;
  };
};

export function D3GraphCanvas({
  nodes,
  edges,
  layoutNonce,
  fitNonce,
  layout,
  labelsVisible,
  onNodeSelect,
  onEdgeSelect,
  onClearSelection,
  onExpandNode,
  hierarchyLabels,
  status,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<D3GraphRenderer | null>(null);
  const callbacksRef = useRef({ onNodeSelect, onEdgeSelect, onClearSelection, onExpandNode });
  const [zoom, setZoom] = useState(1);
  const previousLayoutNonce = useRef(layoutNonce);
  const previousFitNonce = useRef(fitNonce);
  const zoomFrameRef = useRef<number | null>(null);
  const pendingZoomRef = useRef(1);

  const reportZoom = useCallback((nextZoom: number) => {
    pendingZoomRef.current = nextZoom;
    if (zoomFrameRef.current !== null) return;
    zoomFrameRef.current = window.requestAnimationFrame(() => {
      zoomFrameRef.current = null;
      setZoom(pendingZoomRef.current);
    });
  }, []);

  useEffect(() => {
    callbacksRef.current = { onNodeSelect, onEdgeSelect, onClearSelection, onExpandNode };
  }, [onClearSelection, onEdgeSelect, onExpandNode, onNodeSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new D3GraphRenderer(container, {
      onNodeSelect: (node) => callbacksRef.current.onNodeSelect(node),
      onEdgeSelect: (edge) => callbacksRef.current.onEdgeSelect(edge),
      onClearSelection: () => callbacksRef.current.onClearSelection(),
      onExpandNode: (nodeId) => callbacksRef.current.onExpandNode(nodeId),
      onZoomChange: reportZoom,
    });

    rendererRef.current = renderer;

    let resizeFrame: number | null = null;
    let lastSize = {
      width: container.getBoundingClientRect().width,
      height: container.getBoundingClientRect().height,
    };
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver((entries) => {
            const size = entries[0]?.contentRect;
            if (!size || (
              Math.abs(size.width - lastSize.width) <= .5 &&
              Math.abs(size.height - lastSize.height) <= .5
            )) return;
            lastSize = { width: size.width, height: size.height };
            if (resizeFrame !== null) return;
            resizeFrame = window.requestAnimationFrame(() => {
              resizeFrame = null;
              renderer.resize();
            });
          });
    observer?.observe(container);

    return () => {
      observer?.disconnect();
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      if (zoomFrameRef.current !== null) window.cancelAnimationFrame(zoomFrameRef.current);
      renderer.destroy();
      rendererRef.current = null;
    };
  }, [reportZoom]);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    if (hierarchyLabels) renderer.setHierarchyLabels(hierarchyLabels);
    renderer.setLayoutMode(layout);
    renderer.setLabelsVisible(labelsVisible);
    renderer.setData(nodes, edges);
    setZoom(renderer.getZoom());
  }, [nodes, edges, layout, labelsVisible, hierarchyLabels]);

  useEffect(() => {
    if (previousLayoutNonce.current === layoutNonce) return;
    previousLayoutNonce.current = layoutNonce;
    rendererRef.current?.relayout();
  }, [layoutNonce]);

  useEffect(() => {
    if (previousFitNonce.current === fitNonce) return;
    previousFitNonce.current = fitNonce;
    rendererRef.current?.fitToScreen();
  }, [fitNonce]);

  const handleZoomIn = useCallback(() => {
    rendererRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    rendererRef.current?.zoomOut();
  }, []);

  const handleFit = useCallback(() => {
    rendererRef.current?.fitToScreen();
  }, []);

  return (
    <div className="graph-canvas-wrapper">
      <div ref={containerRef} className="d3-canvas" data-testid="graph-canvas" />
      <div className="zoom-controls">
        <button className="zoom-btn" onClick={handleZoomIn} title="Phóng to" aria-label="Phóng to">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4M11 8v6M8 11h6"/></svg>
        </button>
        <button className="zoom-btn" onClick={handleZoomOut} title="Thu nhỏ" aria-label="Thu nhỏ">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4M8 11h6"/></svg>
        </button>
        <button className="zoom-btn" onClick={handleFit} title="Vừa màn hình" aria-label="Vừa màn hình">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/></svg>
        </button>
        <span className="zoom-level">{Math.round(zoom * 100)}%</span>
      </div>
      {status && (
        <div className="graph-canvas-status" aria-hidden="true">
          <span className="graph-live-dot" />
          <strong>{status.nodes}</strong>
          <span>{status.edges}</span>
          <span>{status.detail}</span>
        </div>
      )}
    </div>
  );
}
