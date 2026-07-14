"use client";

import cytoscape, { type Core, type EventObject } from "cytoscape";
import { useEffect, useRef } from "react";
import { coseLayout } from "@/lib/knowledge-graph/graph-layouts";
import { graphStyles } from "@/lib/knowledge-graph/graph-theme";
import type { GraphEdge, GraphNode } from "@/lib/knowledge-graph/types";

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layoutNonce: number;
  fitNonce: number;
  onNodeSelect: (node: GraphNode) => void;
  onEdgeSelect: (edge: GraphEdge) => void;
  onClearSelection: () => void;
  onExpandNode: (nodeId: string) => void;
};

export function GraphCanvas({
  nodes,
  edges,
  layoutNonce,
  fitNonce,
  onNodeSelect,
  onEdgeSelect,
  onClearSelection,
  onExpandNode,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const callbacks = useRef({ onNodeSelect, onEdgeSelect, onClearSelection, onExpandNode });
  const laidOut = useRef(false);
  const previousLayoutNonce = useRef(layoutNonce);
  const previousFitNonce = useRef(fitNonce);

  useEffect(() => {
    callbacks.current = { onNodeSelect, onEdgeSelect, onClearSelection, onExpandNode };
  }, [onClearSelection, onEdgeSelect, onExpandNode, onNodeSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const cy = cytoscape({
      container,
      elements: [],
      style: graphStyles,
      layout: { name: "preset" },
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.18,
    });
    let lastTap = { id: "", at: 0 };
    const selectNode = (event: EventObject) => {
      const node = event.target.data() as GraphNode;
      const now = Date.now();
      if (lastTap.id === node.id && now - lastTap.at < 320) callbacks.current.onExpandNode(node.id);
      lastTap = { id: node.id, at: now };
      callbacks.current.onNodeSelect(node);
    };
    const selectEdge = (event: EventObject) => {
      callbacks.current.onEdgeSelect(event.target.data() as GraphEdge);
    };
    const clearSelection = (event: EventObject) => {
      if (event.target === cy) callbacks.current.onClearSelection();
    };
    const updateZoomLabels = () => {
      cy.nodes().toggleClass("zoomed-out", cy.zoom() < 0.65);
    };
    cy.on("tap", "node", selectNode);
    cy.on("tap", "edge", selectEdge);
    cy.on("tap", clearSelection);
    cy.on("zoom", updateZoomLabels);
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            cy.resize();
          });
    observer?.observe(container);
    cyRef.current = cy;
    return () => {
      observer?.disconnect();
      cy.removeAllListeners();
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const nextIds = new Set([...nodes.map((node) => node.id), ...edges.map((edge) => edge.id)]);
    let addedNodes = 0;
    cy.batch(() => {
      cy.elements().forEach((element) => {
        if (!nextIds.has(element.id())) element.remove();
      });
      nodes.forEach((node) => {
        const existing = cy.getElementById(node.id);
        if (existing.length) existing.data(node);
        else {
          cy.add({ group: "nodes", data: node });
          addedNodes += 1;
        }
      });
      edges.forEach((edge) => {
        const existing = cy.getElementById(edge.id);
        if (existing.length) existing.data(edge);
        else cy.add({ group: "edges", data: edge });
      });
    });
    if (!laidOut.current && nodes.length) {
      cy.layout(coseLayout()).run();
      laidOut.current = true;
    } else if (addedNodes >= 3) {
      cy.layout(coseLayout(true)).run();
    }
  }, [edges, nodes]);

  useEffect(() => {
    if (previousLayoutNonce.current === layoutNonce) return;
    previousLayoutNonce.current = layoutNonce;
    cyRef.current?.layout(coseLayout(true)).run();
  }, [layoutNonce]);

  useEffect(() => {
    if (previousFitNonce.current === fitNonce) return;
    previousFitNonce.current = fitNonce;
    cyRef.current?.fit(undefined, 40);
  }, [fitNonce]);

  return <div ref={containerRef} className="cytoscape-canvas" data-testid="graph-canvas" />;
}
