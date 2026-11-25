import * as d3 from "d3";
import type { GraphEdge, GraphLayoutMode, GraphNode } from "./types";
import { buildHierarchyLayout } from "./hierarchy-layout";
import { buildOrbitLayout } from "./orbit-layout";
import {
  rankRelationshipLabels,
  relationshipLabelBudget,
  isHierarchyEdgeType,
  isHierarchyTreeEdge,
} from "./graph-visualization";
import {
  getNodeColor,
  getEdgeColor,
  getNodeRadius,
  getEdgeWidth,
  getEdgeDash,
  canvasPalette,
  resolveCanvasTheme,
  nodeCardMetrics,
  nodeCardWidth,
  cardEdgePath,
  facingCardEdgePath,
  type CanvasPalette,
  type CanvasTheme,
} from "./d3-graph-styles";
import { graphTypeLabel } from "./graph-theme";

export type D3GraphCallbacks = {
  onNodeSelect: (node: GraphNode) => void;
  onEdgeSelect: (edge: GraphEdge) => void;
  onClearSelection: () => void;
  onExpandNode: (nodeId: string) => void;
  onZoomChange: (zoom: number) => void;
};

type D3Node = GraphNode &
  d3.SimulationNodeDatum & {
    x?: number;
    y?: number;
    cardWidth?: number;
    hierarchyX?: number;
    hierarchyY?: number;
    hierarchyWidth?: number;
    hierarchyHeight?: number;
  };
type D3Edge = Omit<GraphEdge, "source" | "target"> &
  Pick<d3.SimulationLinkDatum<D3Node>, "index"> & {
    source: string | D3Node;
    target: string | D3Node;
  };

const HIERARCHY_NODE_WIDTH = 184;
const HIERARCHY_NODE_HEIGHT = 64;
const HIERARCHY_BOARD_HEIGHT = 76;
const HIERARCHY_LIST_NODE_WIDTH = 156;
const HIERARCHY_LIST_NODE_HEIGHT = 48;
const DEFAULT_MIN_ZOOM = .05;
const MAX_ZOOM = 4;

type DragState = {
  nodeId: string;
  identifier: "mouse" | number;
  pointerOffset: [number, number];
  origins: Array<{
    node: D3Node;
    x: number;
    y: number;
    fx: number | null | undefined;
    fy: number | null | undefined;
  }>;
  moved: boolean;
};

type HierarchyLabels = {
  board: string;
  nodes: string;
  open: string;
  close: string;
};

export function isHierarchyBoard(node: Pick<GraphNode, "type">): boolean {
  return node.type === "SystemPillar";
}

function hierarchyNodeHeight(
  node: Pick<GraphNode, "type" | "collapsed_leaf_count" | "leaf_group_expanded"> & { hierarchyHeight?: number },
): number {
  if (node.hierarchyHeight) return node.hierarchyHeight;
  if ((node.collapsed_leaf_count ?? 0) > 0 || node.leaf_group_expanded) return HIERARCHY_BOARD_HEIGHT;
  if (isHierarchyBoard(node)) return HIERARCHY_BOARD_HEIGHT;
  return node.type === "SystemRoot" ? HIERARCHY_NODE_HEIGHT : HIERARCHY_LIST_NODE_HEIGHT;
}

function hierarchyNodeWidth(
  node: Pick<GraphNode, "type"> & { hierarchyWidth?: number },
): number {
  if (node.hierarchyWidth) return node.hierarchyWidth;
  return ["SystemRoot", "SystemPillar"].includes(node.type)
    ? HIERARCHY_NODE_WIDTH
    : HIERARCHY_LIST_NODE_WIDTH;
}

/**
 * The footer line under a board card.
 *
 * A board with nothing in it must not offer to open: ten of the eleven pillars were in
 * that state and invited a click that could only ever produce a blank canvas.
 */
export function boardFooter(
  node: Pick<GraphNode, "child_count">,
  expanded: boolean,
  labels: HierarchyLabels,
): string {
  const count = node.child_count ?? 0;
  if (expanded) return `${count} ${labels.nodes} · ${labels.close} ↑`;
  if (count === 0) return `☷ 0 ${labels.nodes}`;
  return `☷ ${count} ${labels.nodes} · ${labels.open} →`;
}

function graphEdge(edge: D3Edge): GraphEdge {
  const source = typeof edge.source === "object" ? edge.source.id : edge.source;
  const target = typeof edge.target === "object" ? edge.target.id : edge.target;
  return { ...edge, source, target };
}

export function relationshipFocusProjection(
  focusId: string | null,
  adjacency: ReadonlyMap<string, ReadonlySet<string>>,
  incidentEdges: ReadonlyMap<string, ReadonlySet<string>>,
  labelRanks: ReadonlyMap<string, number>,
) {
  if (!focusId) {
    return {
      focusId: null,
      neighborNodeIds: new Set<string>(),
      incidentEdgeIds: new Set<string>(),
      labelNodeIds: new Set<string>(),
    };
  }
  const neighborNodeIds = new Set(adjacency.get(focusId) ?? []);
  const rankedNeighborIds = [...neighborNodeIds]
    .sort((left, right) =>
      (labelRanks.get(left) ?? Infinity) - (labelRanks.get(right) ?? Infinity) ||
      left.localeCompare(right),
    )
    .slice(0, 16);
  return {
    focusId,
    neighborNodeIds,
    incidentEdgeIds: new Set(incidentEdges.get(focusId) ?? []),
    labelNodeIds: new Set([focusId, ...rankedNeighborIds]),
  };
}

export type GraphFitInsets = {
  top: number;
  right: number;
  bottom: number;
  left: number;
};

export function graphFitTransform(
  bounds: Pick<DOMRect, "x" | "y" | "width" | "height">,
  viewportWidth: number,
  viewportHeight: number,
  insets: GraphFitInsets,
) {
  const availableWidth = Math.max(1, viewportWidth - insets.left - insets.right);
  const availableHeight = Math.max(1, viewportHeight - insets.top - insets.bottom);
  const contentWidth = Math.max(1, bounds.width);
  const contentHeight = Math.max(1, bounds.height);
  const scale = Math.min(availableWidth / contentWidth, availableHeight / contentHeight, 2);
  const midX = bounds.x + bounds.width / 2;
  const midY = bounds.y + bounds.height / 2;

  return {
    x: insets.left + availableWidth / 2 - scale * midX,
    y: insets.top + availableHeight / 2 - scale * midY,
    scale,
  };
}

export function dimensionsChanged(
  previous: { width: number; height: number },
  next: { width: number; height: number },
  tolerance = .5,
) {
  return Math.abs(previous.width - next.width) > tolerance ||
    Math.abs(previous.height - next.height) > tolerance;
}

export class D3GraphRenderer {
  private svg!: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private container!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private simulation!: d3.Simulation<D3Node, D3Edge>;
  private nodesGroup!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private edgesGroup!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private labelsGroup!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private communitiesGroup!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private zoomBehavior!: d3.ZoomBehavior<SVGSVGElement, unknown>;
  private width = 0;
  private height = 0;
  private nodes: D3Node[] = [];
  private edges: D3Edge[] = [];
  private selectedNodeId: string | null = null;
  private selectedEdgeId: string | null = null;
  private hoveredNodeId: string | null = null;
  private hoveredEdgeId: string | null = null;
  private keyboardEdgeId: string | null = null;
  private relationshipLabelRanks = new Map<string, number>();
  private adjacency = new Map<string, Set<string>>();
  private incidentEdges = new Map<string, Set<string>>();
  private nodeElementById = new Map<string, SVGGElement>();
  private edgeElementById = new Map<string, SVGElement>();
  private edgeDataById = new Map<string, D3Edge>();
  private nodeDataById = new Map<string, D3Node>();
  private theme: CanvasTheme = "light";
  private palette: CanvasPalette = canvasPalette("light");
  private themeObserver: MutationObserver | null = null;
  private themeMedia: MediaQueryList | null = null;
  private onThemeMediaChange: (() => void) | null = null;
  private activeDrag: DragState | null = null;
  private touchingCanvas = false;
  private pendingData: { nodes: GraphNode[]; edges: GraphEdge[] } | null = null;
  private layoutFrame: number | null = null;
  private fitAfterLayout = false;
  private orbitRadii: number[] = [];
  private appliedRelationshipFocusId: string | null = null;
  private appliedFocusNodeIds = new Set<string>();
  private appliedFocusEdgeIds = new Set<string>();
  private appliedHoverEdgeIds = new Set<string>();
  private appliedHierarchyHoverEdgeIds = new Set<string>();
  private currentZoom = 1;
  private callbacks: D3GraphCallbacks;
  private lastTap = { id: "", at: 0 };
  private layoutMode: GraphLayoutMode = "relationship";
  private hierarchyLabels: HierarchyLabels = {
    board: "Bảng",
    nodes: "nút",
    open: "Mở",
    close: "Thu gọn",
  };

  constructor(
    private containerElement: HTMLDivElement,
    callbacks: D3GraphCallbacks,
  ) {
    this.callbacks = callbacks;
    this.init();
  }

  private init() {
    const rect = this.containerElement.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    this.theme = resolveCanvasTheme(document.documentElement);
    this.palette = canvasPalette(this.theme);

    this.svg = d3
      .select(this.containerElement)
      .append("svg")
      .attr("width", this.width)
      .attr("height", this.height)
      .attr("class", "d3-graph-svg")
      .style("touch-action", "none");

    this.container = this.svg.append("g").attr("class", "d3-graph-container");

    const defs = this.svg.append("defs");

    const arrow = defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 14)
      .attr("refY", 0)
      .attr("markerWidth", 5)
      .attr("markerHeight", 5)
      .attr("orient", "auto");
    arrow.append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", this.palette.edgeArrow);

    const edgeGradient = defs.append("linearGradient")
      .attr("id", "d3-hierarchy-edge")
      .attr("x1", "0%").attr("y1", "50%").attr("x2", "100%").attr("y2", "50%");
    edgeGradient.append("stop").attr("offset", "0%").attr("stop-color", "#8aa8b2").attr("stop-opacity", "0.7");
    edgeGradient.append("stop").attr("offset", "100%").attr("stop-color", "#0b6f76").attr("stop-opacity", "0.85");

    const edgeGradientHover = defs.append("linearGradient")
      .attr("id", "d3-hierarchy-edge-active")
      .attr("x1", "0%").attr("y1", "50%").attr("x2", "100%").attr("y2", "50%");
    edgeGradientHover.append("stop").attr("offset", "0%").attr("stop-color", "#5969d8").attr("stop-opacity", "0.9");
    edgeGradientHover.append("stop").attr("offset", "100%").attr("stop-color", "#0b6f76").attr("stop-opacity", "1");

    this.communitiesGroup = this.container.append("g").attr("class", "d3-communities");
    this.edgesGroup = this.container.append("g").attr("class", "d3-edges");
    this.nodesGroup = this.container.append("g").attr("class", "d3-nodes");
    this.labelsGroup = this.container.append("g").attr("class", "d3-labels");

    this.zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([DEFAULT_MIN_ZOOM, MAX_ZOOM])
      .filter((event) => !this.activeDrag && (!event.ctrlKey || event.type === "wheel") && !event.button)
      .on("start", (event) => {
        if (event.sourceEvent) this.fitAfterLayout = false;
      })
      .on("zoom", (event) => {
        this.currentZoom = event.transform.k;
        this.container.attr("transform", event.transform);
        this.updateOrbitLabels();
        this.callbacks.onZoomChange(this.currentZoom);
      });

    this.svg.call(this.zoomBehavior);
    this.bindTouchDrag();

    this.svg.on("click", (event) => {
      if (event.target === this.svg.node()) {
        this.callbacks.onClearSelection();
        this.setSelection(null, null);
      }
    });

    this.simulation = d3
      .forceSimulation<D3Node>()
      .force("charge", d3.forceManyBody<D3Node>().strength(-350))
      .force("link", d3.forceLink<D3Node, D3Edge>().id((d) => d.id).distance(80))
      .force("center", d3.forceCenter(this.width / 2, this.height / 2))
      .force("collision", d3.forceCollide<D3Node>().radius((d) => getNodeRadius(d.type, d.degree) + 8))
      .force("x", d3.forceX(this.width / 2).strength(0.1))
      .force("y", d3.forceY(this.height / 2).strength(0.1))
      .alphaDecay(0.02)
      .on("tick", () => this.tick());

    this.simulation.stop();
    this.observeTheme();
  }

  private observeTheme() {
    if (typeof MutationObserver !== "undefined") {
      this.themeObserver = new MutationObserver(() => this.refreshTheme());
      this.themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      this.themeMedia = window.matchMedia("(prefers-color-scheme: dark)");
      this.onThemeMediaChange = () => this.refreshTheme();
      this.themeMedia.addEventListener?.("change", this.onThemeMediaChange);
    }
  }

  private readTheme() {
    const next = resolveCanvasTheme(document.documentElement);
    if (next === this.theme) return false;
    this.theme = next;
    this.palette = canvasPalette(next);
    this.svg.select("#arrowhead path").attr("fill", this.palette.edgeArrow);
    return true;
  }

  private refreshTheme() {
    if (this.activeDrag || this.touchingCanvas || !this.readTheme()) return;
    this.clearRelationshipHoverEdges();
    this.clearHierarchyHoverEdges();
    this.clearRelationshipFocusClasses();
    const restoreFocus = this.render();
    this.updateSelection();
    this.tick();
    restoreFocus();
  }

  setLayoutMode(mode: GraphLayoutMode) {
    if (this.layoutMode === mode) return;
    this.finishDrag(true, false);
    this.touchingCanvas = false;
    this.readTheme();
    this.pendingData = null;
    this.stopRelationshipLayout();
    this.clearRelationshipHoverEdges();
    this.clearHierarchyHoverEdges();
    this.clearRelationshipFocusClasses();
    this.layoutMode = mode;
    this.edgesGroup.selectAll("*").remove();
    this.nodesGroup.selectAll("*").remove();
    this.communitiesGroup.selectAll("*").remove();
    this.configureForces();
  }

  setSelection(nodeId: string | null, edgeId: string | null) {
    if (this.selectedNodeId === nodeId && this.selectedEdgeId === edgeId) return;
    this.selectedNodeId = nodeId;
    this.selectedEdgeId = edgeId;
    this.updateSelection();
  }

  setLabelsVisible(visible: boolean) {
    this.svg.classed("d3-labels-hidden", !visible);
  }

  setHierarchyLabels(labels: HierarchyLabels) {
    this.hierarchyLabels = labels;
  }

  private configureForces() {
    if (this.layoutMode === "hierarchy" || this.layoutMode === "orbit") {
      this.simulation
        .force("charge", null)
        .force("link", null)
        .force("center", null)
        .force("collision", null)
        .force("x", null)
        .force("y", null);
      return;
    }

    const types = [...new Set(this.nodes.map((node) => node.type))].sort();
    const columns = Math.max(1, Math.ceil(Math.sqrt(types.length)));
    const rows = Math.max(1, Math.ceil(types.length / columns));
    const anchors = new Map(types.map((type, index) => [
      type,
      {
        x: ((index % columns) + .5) * (this.width / columns),
        y: (Math.floor(index / columns) + .5) * (this.height / rows),
      },
    ]));

    this.simulation
      .force("charge", d3.forceManyBody<D3Node>().strength((node) => -75 - Math.min(node.degree * 4, 90)))
      .force("link", d3.forceLink<D3Node, D3Edge>().id((d) => d.id).distance(86).strength(.22))
      .force("center", d3.forceCenter(this.width / 2, this.height / 2))
      .force("collision", d3.forceCollide<D3Node>().radius((d) => Math.max((d.cardWidth ?? 120) / 2, getNodeRadius(d.type, d.degree) + 10)).iterations(2))
      .force("x", d3.forceX<D3Node>((node) => anchors.get(node.type)?.x ?? this.width / 2).strength(.19))
      .force("y", d3.forceY<D3Node>((node) => anchors.get(node.type)?.y ?? this.height / 2).strength(.19))
      .alphaDecay(0.04);
  }

  private applyOrbitPositions() {
    if (this.layoutMode !== "orbit") return;
    const ranked = [...this.nodes].sort((left, right) =>
      right.degree - left.degree ||
      right.source_count - left.source_count ||
      left.type.localeCompare(right.type) ||
      left.label.localeCompare(right.label) ||
      left.id.localeCompare(right.id),
    );
    const count = Math.max(1, ranked.length);
    const ringGroups: D3Node[][] = [[], [], [], []];
    ranked.forEach((node, index) => {
      const ratio = index / count;
      const ring = ratio < .04 ? 0 : ratio < .2 ? 1 : ratio < .55 ? 2 : 3;
      ringGroups[ring].push(node);
    });
    ringGroups.forEach((group) => {
      group.sort((left, right) => left.type.localeCompare(right.type) || left.label.localeCompare(right.label));
    });
    const { positions, radii } = buildOrbitLayout(ringGroups, this.width, this.height);
    this.orbitRadii = radii;
    this.nodes.forEach((node) => {
      if (node.fx != null || node.fy != null) return;
      const position = positions.get(node.id);
      if (!position) return;
      node.x = position.x;
      node.y = position.y;
    });
  }

  private applyHierarchyPositions() {
    if (this.layoutMode !== "hierarchy") return;
    const positions = buildHierarchyLayout(
      this.nodes,
      this.edges.map(graphEdge),
      this.width,
      this.height,
    );
    this.nodes.forEach((node) => {
      const position = positions.get(node.id);
      node.hierarchyX = position?.x ?? this.width / 2;
      node.hierarchyY = position?.y ?? this.height / 2;
      node.hierarchyWidth = position?.width;
      node.hierarchyHeight = position?.height;
      // A node the user dragged keeps its placement (relayout clears the pin first).
      if (node.fx != null || node.fy != null) return;
      node.x = node.hierarchyX;
      node.y = node.hierarchyY;
    });
    // Children without their own placement inherit their board's manual offset.
    this.nodes.filter((node) => isHierarchyBoard(node) && node.expanded_group).forEach((board) => {
      const dx = (board.x ?? 0) - (board.hierarchyX ?? 0);
      const dy = (board.y ?? 0) - (board.hierarchyY ?? 0);
      this.boardChildren(board).forEach((node) => {
        if (node.fx != null || node.fy != null) return;
        node.x = (node.x ?? 0) + dx;
        node.y = (node.y ?? 0) + dy;
      });
    });
  }

  setData(nodes: GraphNode[], edges: GraphEdge[], fit = true) {
    // D3 keeps the original datum and touch target for the duration of the gesture.
    if (this.activeDrag || this.touchingCanvas) {
      this.pendingData = { nodes, edges };
      return;
    }
    this.stopRelationshipLayout();
    this.clearRelationshipHoverEdges();
    this.clearHierarchyHoverEdges();
    this.clearRelationshipFocusClasses();
    const types = [...new Set(nodes.map((node) => node.type))].sort();
    const columns = Math.max(1, Math.ceil(Math.sqrt(types.length)));
    const rows = Math.max(1, Math.ceil(types.length / columns));
    const typeIndex = new Map(types.map((type, index) => [type, index]));
    const stableUnit = (value: string, salt: number) => {
      let hash = 2166136261 + salt;
      for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0) / 4294967295;
    };
    this.nodes = nodes.map((n) => {
      const existing = this.nodeDataById.get(n.id);
      const cardWidth = this.layoutMode === "hierarchy"
        ? undefined
        : nodeCardWidth(n.label, n.degree, this.layoutMode === "relationship" ? graphTypeLabel(n.type).toUpperCase() : undefined);
      if (this.layoutMode !== "relationship") {
        return {
          ...n,
          cardWidth,
          x: existing?.x ?? this.width / 2,
          y: existing?.y ?? this.height / 2,
          fx: existing?.fx,
          fy: existing?.fy,
        };
      }
      // Free-drag contract: a refresh keeps the position the user gave each node, so
      // exploration never yanks a canvas they just arranged. New nodes still scatter.
      if (existing && existing.x !== undefined && existing.y !== undefined) {
        return { ...n, cardWidth, x: existing.x, y: existing.y, fx: existing.fx, fy: existing.fy };
      }
      const index = typeIndex.get(n.type) ?? 0;
      const anchorX = ((index % columns) + .5) * (this.width / columns);
      const anchorY = (Math.floor(index / columns) + .5) * (this.height / rows);
      const spreadX = Math.max(80, this.width / columns * .62);
      const spreadY = Math.max(80, this.height / rows * .62);
      return {
        ...n,
        x: anchorX + (stableUnit(n.id, 17) - .5) * spreadX,
        y: anchorY + (stableUnit(n.id, 53) - .5) * spreadY,
      };
    });

    const renderedNodeMap = new Map(this.nodes.map((node) => [node.id, node]));
    this.edges = edges.flatMap<D3Edge>((edge) => {
      const source = renderedNodeMap.get(edge.source);
      const target = renderedNodeMap.get(edge.target);
      if (!source || !target) return [];
      if (this.layoutMode === "hierarchy") return [{ ...edge, source, target }];
      return [{ ...edge }];
    });

    this.relationshipLabelRanks = rankRelationshipLabels(this.nodes);
    this.nodeDataById = renderedNodeMap;
    this.edgeDataById = new Map(this.edges.map((edge) => [edge.id, edge]));
    this.adjacency = new Map(this.nodes.map((node) => [node.id, new Set<string>()]));
    this.incidentEdges = new Map(this.nodes.map((node) => [node.id, new Set<string>()]));
    this.edges.forEach((edge) => {
      const safeEdge = graphEdge(edge);
      this.adjacency.get(safeEdge.source)?.add(safeEdge.target);
      this.adjacency.get(safeEdge.target)?.add(safeEdge.source);
      this.incidentEdges.get(safeEdge.source)?.add(safeEdge.id);
      this.incidentEdges.get(safeEdge.target)?.add(safeEdge.id);
    });

    this.applyHierarchyPositions();
    this.applyOrbitPositions();
    this.configureForces();

    this.simulation.nodes(this.nodes);
    const linkForce = this.simulation.force("link") as d3.ForceLink<D3Node, D3Edge> | null;
    linkForce?.links(this.edges);

    const restoreFocus = this.render();
    this.updateSelection();
    if (this.layoutMode === "hierarchy" || this.layoutMode === "orbit") {
      this.simulation.stop();
      this.tick();
      if (fit) {
        if (this.layoutMode === "hierarchy") this.openHierarchyAtReadableScale();
        else this.fitToScreen();
      }
      restoreFocus();
      return;
    }
    this.settleRelationshipLayout(90, .72, fit);
    restoreFocus();
  }

  private settleRelationshipLayout(iterations: number, alpha: number, fit = true) {
    if (this.layoutMode !== "relationship") return;
    this.stopRelationshipLayout();
    this.simulation.alpha(alpha).alphaTarget(0);
    if (this.nodes.length < 180 && this.edges.length < 600) {
      this.simulation.tick(iterations);
      this.tick();
      if (fit) this.fitToScreen(false);
      return;
    }

    this.tick();
    if (fit) this.fitToScreen(false);
    this.fitAfterLayout = fit;
    let remaining = iterations;
    const advance = () => {
      this.layoutFrame = null;
      const deadline = performance.now() + 8;
      do {
        this.simulation.tick();
        remaining -= 1;
      } while (remaining > 0 && performance.now() < deadline);
      this.tick();
      if (remaining > 0) {
        this.layoutFrame = requestAnimationFrame(advance);
      } else if (this.fitAfterLayout) {
        this.fitAfterLayout = false;
        this.fitToScreen(false);
      }
    };
    this.layoutFrame = requestAnimationFrame(advance);
  }

  private stopRelationshipLayout() {
    this.simulation.stop();
    if (this.layoutFrame !== null) cancelAnimationFrame(this.layoutFrame);
    this.layoutFrame = null;
    this.fitAfterLayout = false;
  }

  private render() {
    const active = document.activeElement;
    const focused = active?.closest(".d3-node, .d3-edge");
    const nodeId = focused?.getAttribute("data-node-id");
    const edgeId = focused?.getAttribute("data-edge-id");
    const restore = focused && this.svg.node()?.contains(focused);
    this.renderCommunities();
    this.renderEdges();
    this.renderNodes();
    this.renderLabels();
    return () => {
      if (!restore || !active || active.isConnected || document.activeElement !== document.body) return;
      const replacement = nodeId ? this.nodeElementById.get(nodeId) : this.edgeElementById.get(edgeId ?? "");
      const next = replacement && replacement.getAttribute("display") !== "none"
        ? replacement
        : this.nodesGroup.select<SVGGElement>(".d3-node").node();
      next?.focus({ preventScroll: true });
    };
  }

  private renderCommunities() {
    this.communitiesGroup.selectAll("*").remove();
    if (this.layoutMode === "hierarchy") return;
    if (this.layoutMode === "orbit") {
      this.orbitRadii.forEach((radius, index) => {
        this.communitiesGroup
          .append("circle")
          .attr("class", "d3-orbit-ring")
          .attr("data-ring", index)
          .attr("cx", this.width / 2)
          .attr("cy", this.height / 2)
          .attr("r", radius);
      });
      return;
    }
    const types = [...new Set(this.nodes.map((node) => node.type))]
      .filter((type) => this.nodes.filter((node) => node.type === type).length > 1);
    const groups = this.communitiesGroup
      .selectAll<SVGGElement, string>("g.d3-community")
      .data(types)
      .enter()
      .append("g")
      .attr("class", "d3-community")
      .attr("data-community", (type) => type);
    groups.append("circle").attr("class", "d3-community-halo");
  }

  private edgeIsHidden(edge: D3Edge) {
    const source = typeof edge.source === "object" ? edge.source : this.nodeDataById.get(edge.source);
    return this.layoutMode === "hierarchy" && isHierarchyTreeEdge(edge) && Boolean(source?.expanded_group);
  }

  private renderEdges() {
    const hierarchy = this.layoutMode === "hierarchy";
    const select = (edge: D3Edge) => {
      this.callbacks.onEdgeSelect(graphEdge(edge));
      this.setSelection(null, edge.id);
    };
    const paths = this.edgesGroup
      .selectAll<SVGPathElement, D3Edge>("path.d3-edge")
      .data(this.edges, (edge) => edge.id)
      .join((enter) => enter
        .append("path")
        .attr("data-edge-id", (edge) => edge.id)
        .attr("role", "button")
        .attr("fill", "none")
        .attr("stroke-linecap", "round")
        .attr("marker-end", "url(#arrowhead)")
        .attr("aria-keyshortcuts", "ArrowUp ArrowDown Enter Space")
        .on("click", (event, edge) => {
          event.stopPropagation();
          select(edge);
        })
        .on("keydown", (event, edge) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            select(edge);
          } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
            event.preventDefault();
            this.focusAdjacentEdge(edge.id, event.key === "ArrowDown" ? 1 : -1);
          }
        })
        .on("focus", (event, edge) => {
          const element = event.currentTarget as SVGElement;
          this.setKeyboardEdge(edge.id);
          element.classList.add("d3-edge-hovered");
          if (element.matches(":focus-visible")) this.revealEdge(edge);
        })
        .on("blur", (event) => {
          const element = event.currentTarget as SVGElement;
          element.classList.toggle("d3-edge-hovered", element.matches(":hover"));
        })
        .on("mouseenter", (event, edge) => {
          (event.currentTarget as SVGElement).classList.add("d3-edge-hovered");
          this.hoveredEdgeId = edge.id;
          this.updateHover();
        })
        .on("mouseleave", (event) => {
          const element = event.currentTarget as SVGElement;
          element.classList.toggle("d3-edge-hovered", document.activeElement === element);
          this.hoveredEdgeId = null;
          this.updateHover();
        }));

    this.edgeElementById.clear();
    paths
      .attr("class", (edge) => {
        if (hierarchy) return isHierarchyTreeEdge(edge) ? "d3-edge d3-hierarchy-edge" : "d3-edge d3-hierarchy-relation-edge";
        return this.layoutMode === "relationship" ? "d3-edge d3-network-edge" : "d3-edge d3-orbit-edge";
      })
      .attr("display", (edge) => this.edgeIsHidden(edge) ? "none" : null)
      .attr("aria-label", (edge) => {
        const { source, target, type } = graphEdge(edge);
        return `${this.nodeDataById.get(source)?.label ?? source} → ${this.nodeDataById.get(target)?.label ?? target} · ${type}`;
      })
      .attr("stroke-dasharray", (edge) => hierarchy && !isHierarchyTreeEdge(edge) ? "4 5" : getEdgeDash(edge.type))
      .attr("tabindex", (edge) => this.edgeIsHidden(edge) ? null : -1)
      .each((edge, index, elements) => this.edgeElementById.set(edge.id, elements[index]));
    const first = this.edges.find((edge) => !this.edgeIsHidden(edge));
    const previous = this.keyboardEdgeId && this.edgeDataById.get(this.keyboardEdgeId);
    this.setKeyboardEdge(previous && !this.edgeIsHidden(previous) ? previous.id : first?.id ?? null);
  }

  private setKeyboardEdge(edgeId: string | null) {
    if (this.keyboardEdgeId) {
      const previous = this.edgeElementById.get(this.keyboardEdgeId);
      if (previous?.getAttribute("display") !== "none") previous?.setAttribute("tabindex", "-1");
    }
    this.keyboardEdgeId = edgeId;
    if (edgeId) this.edgeElementById.get(edgeId)?.setAttribute("tabindex", "0");
  }

  private focusAdjacentEdge(edgeId: string, offset: number) {
    const visible = this.edges.filter((edge) => !this.edgeIsHidden(edge));
    if (visible.length === 0) return;
    const index = visible.findIndex((edge) => edge.id === edgeId);
    const next = visible[(index + offset + visible.length) % visible.length];
    this.edgeElementById.get(next.id)?.focus({ preventScroll: true });
  }

  private revealEdge(edge: D3Edge) {
    // A single edge may span the entire graph. Reveal its source as the stable endpoint.
    const source = typeof edge.source === "object" ? edge.source : this.nodeDataById.get(edge.source);
    if (source) this.revealNode(source);
  }

  private revealNode(node: D3Node) {
    if (this.activeDrag || this.touchingCanvas) return;
    const transform = d3.zoomTransform(this.svg.node()!);
    const x = transform.applyX(node.x ?? 0);
    const y = transform.applyY(node.y ?? 0);
    const width = (this.layoutMode === "hierarchy" ? hierarchyNodeWidth(node) : node.cardWidth ?? 120) * transform.k;
    const height = (this.layoutMode === "hierarchy" ? hierarchyNodeHeight(node) : 44) * transform.k;
    const margin = 22;
    const minX = Math.min(this.width / 2, margin + width / 2);
    const minY = Math.min(this.height / 2, margin + height / 2);
    const dx = Math.max(minX, Math.min(this.width - minX, x)) - x;
    const dy = Math.max(minY, Math.min(this.height - minY, y)) - y;
    if (Math.abs(dx) < .5 && Math.abs(dy) < .5) return;
    this.fitAfterLayout = false;
    this.svg.call(this.zoomBehavior.transform, transform.translate(dx / transform.k, dy / transform.k));
  }

  private renderNodes() {
    const hierarchy = this.layoutMode === "hierarchy";
    const relationship = this.layoutMode === "relationship";
    if (hierarchy) this.nodesGroup.selectAll("*").remove();
    const nodes = this.nodesGroup
      .selectAll<SVGGElement, D3Node>(".d3-node")
      .data(this.nodes, (d) => d.id);

    nodes.exit().remove();

    const nodesEnter = nodes
      .enter()
      .append("g")
      .attr("class", (d) => hierarchy
        ? `d3-node d3-hierarchy-node${isHierarchyBoard(d) ? " d3-hierarchy-board" : ""}${d.expanded_group ? " d3-hierarchy-board-expanded" : ""}`
        : "d3-node")
      .attr("data-node-id", (d) => d.id)
      .attr("data-node-type", (d) => d.type)
      // Every node is reachable from the keyboard, not only the hierarchy boards. A graph
      // whose nodes can be clicked but not tabbed to is unusable without a mouse.
      .attr("role", "button")
      .attr("tabindex", 0)
      .style("touch-action", "none")
      .on("click", (event, d) => {
        event.stopPropagation();
        const now = Date.now();
        const openBoard = this.layoutMode === "hierarchy" &&
          ((isHierarchyBoard(d) && (d.child_count ?? 0) > 0) ||
            (d.collapsed_leaf_count ?? 0) > 0 || d.leaf_group_expanded);
        if (openBoard || (this.lastTap.id === d.id && now - this.lastTap.at < 320)) {
          this.callbacks.onExpandNode(d.id);
        }
        this.lastTap = { id: d.id, at: now };
        this.callbacks.onNodeSelect(d);
        this.setSelection(d.id, null);
      })
      .on("keydown", (event, d) => {
        if (!["Enter", " "].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        this.callbacks.onNodeSelect(d);
        this.setSelection(d.id, null);
        // Enter opens a node that has somewhere to go; on a leaf it simply selects,
        // matching what a click does.
        const canOpen = this.layoutMode === "hierarchy"
          ? (d.child_count ?? 0) > 0 || (d.collapsed_leaf_count ?? 0) > 0 || Boolean(d.leaf_group_expanded)
          : (d.degree ?? 0) > 0;
        if (canOpen) this.callbacks.onExpandNode(d.id);
      })
      .on("focus", (event, d) => {
        const element = event.currentTarget as SVGGElement;
        element.classList.add("d3-node-hovered");
        if (element.matches(":focus-visible")) this.revealNode(d);
        this.hoveredNodeId = d.id;
        this.updateHover();
      })
      .on("blur", (event) => {
        (event.currentTarget as SVGGElement).classList.remove("d3-node-hovered");
        this.hoveredNodeId = null;
        this.updateHover();
      })
      .on("mouseenter", (event, d) => {
        (event.currentTarget as SVGGElement).classList.add("d3-node-hovered");
        this.hoveredNodeId = d.id;
        this.updateHover();
      })
      .on("mouseleave", (event) => {
        const element = event.currentTarget as SVGGElement;
        if (document.activeElement === element && element.matches(":focus-visible")) return;
        element.classList.remove("d3-node-hovered");
        this.hoveredNodeId = null;
        this.updateHover();
      });

    nodesEnter.call(this.drag());
    const callbacks = this.callbacks;
    const hierarchyLabels = this.hierarchyLabels;
    const palette = this.palette;
    nodesEnter.each(function (d) {
      const group = d3.select(this);
      if (hierarchy) {
        const color = getNodeColor(d.type);
        const height = hierarchyNodeHeight(d);
        const width = hierarchyNodeWidth(d);
        const board = isHierarchyBoard(d);
        const expandedBoard = board && Boolean(d.expanded_group);
        const headerTop = -height / 2;
        group
          .append("rect")
          .attr("class", "d3-node-glyph d3-hierarchy-card")
          .attr("x", -width / 2)
          .attr("y", -height / 2)
          .attr("width", width)
          .attr("height", height)
          .attr("rx", 10)
          .attr("fill", expandedBoard ? palette.hierarchyBoardFillExpanded : board ? palette.hierarchyBoardFill : palette.hierarchyCardFill)
          .attr("stroke", palette.cardStroke)
          .attr("stroke-width", 1.5);
        group
          .append("rect")
          .attr("class", "d3-hierarchy-accent")
          .attr("x", -width / 2)
          .attr("y", -height / 2)
          .attr("width", 6)
          .attr("height", expandedBoard ? 64 : height)
          .attr("rx", 3)
          .attr("fill", color);
        if (expandedBoard) {
          group
            .append("line")
            .attr("class", "d3-hierarchy-board-divider")
            .attr("x1", -width / 2)
            .attr("x2", width / 2)
            .attr("y1", headerTop + 64)
            .attr("y2", headerTop + 64);
        }
        group
          .append("text")
          .attr("class", "d3-hierarchy-type")
          .attr("x", -width / 2 + 18)
          .attr("y", expandedBoard ? headerTop + 20 : board ? -16 : -9)
          .attr("font-size", "9px")
          .attr("font-weight", "750")
          .attr("fill", color)
          .text(graphTypeLabel(d.type).toUpperCase());
        group
          .append("text")
          .attr("class", "d3-node-label")
          .attr("x", -width / 2 + 18)
          .attr("y", expandedBoard ? headerTop + 43 : board ? 4 : 13)
          .attr("font-size", "12px")
          .attr("font-weight", "700")
          .attr("fill", palette.labelText)
          .text(d.label.length > (expandedBoard ? 46 : board ? 24 : 20)
            ? d.label.slice(0, expandedBoard ? 46 : board ? 24 : 20) + "…"
            : d.label);
        if (board) {
          group
            .append("text")
            .attr("class", "d3-hierarchy-board-action")
            .attr("x", expandedBoard ? width / 2 - 18 : -width / 2 + 18)
            .attr("y", expandedBoard ? headerTop + 37 : 25)
            .attr("text-anchor", expandedBoard ? "end" : "start")
            .attr("font-size", "9px")
            .attr("font-weight", "700")
            .attr("fill", palette.hierarchyAction)
            .text(boardFooter(d, expandedBoard, hierarchyLabels));
        }
        if ((d.collapsed_leaf_count ?? 0) > 0 || d.leaf_group_expanded) {
          const expandedLeaves = Boolean(d.leaf_group_expanded);
          group
            .append("g")
            .attr("class", "d3-hierarchy-leaf-action")
            .attr("role", "button")
            .attr("aria-label", `${expandedLeaves ? hierarchyLabels.close : hierarchyLabels.open} nút lá của ${d.label}`)
            .on("click", (event) => {
              event.stopPropagation();
              callbacks.onExpandNode(d.id);
            })
            .call((action) => {
              action.append("rect")
                .attr("x", -width / 2 + 14)
                .attr("y", height / 2 - 25)
                .attr("width", width - 28)
                .attr("height", 18)
                .attr("rx", 9);
              action.append("text")
                .attr("x", 0)
                .attr("y", height / 2 - 12)
                .attr("text-anchor", "middle")
                .text(expandedLeaves
                  ? `${hierarchyLabels.close} nút lá ↑`
                  : `+${d.collapsed_leaf_count ?? 0} đang ẩn · ${hierarchyLabels.open} →`);
            });
        }
        if (d.primary_parent_id) {
          group
            .append("circle")
            .attr("class", "d3-hierarchy-port input")
            .attr("cx", -width / 2)
            .attr("cy", 0)
            .attr("r", 4.5);
        }
        if ((d.child_count ?? 0) > 0 && !expandedBoard) {
          group
            .append("circle")
            .attr("class", "d3-hierarchy-port output")
            .attr("cx", width / 2)
            .attr("cy", 0)
            .attr("r", 7)
            .attr("role", "button")
            .attr("aria-label", `Open child branch for ${d.label}`)
            .on("click", (event) => {
              event.stopPropagation();
              callbacks.onExpandNode(d.id);
            });
          group
            .append("text")
            .attr("class", "d3-hierarchy-child-count")
            .attr("x", width / 2 - 14)
            .attr("y", -13)
            .attr("text-anchor", "end")
            .text(String(d.child_count));
        }
        group.append("title").text(`${d.label} · ${graphTypeLabel(d.type)}`);
        return;
      }
      const color = getNodeColor(d.type);
      const visibleLabel = d.label.length > 26 ? `${d.label.slice(0, 26)}…` : d.label;
      const visibleType = graphTypeLabel(d.type).toUpperCase();
      const metrics = nodeCardMetrics(visibleLabel, d.degree);
      const cardWidth = nodeCardWidth(d.label, d.degree, relationship ? visibleType : undefined);
      d.cardWidth = cardWidth;

      // Weave-style node card: one rounded surface with a type accent, thin border and the
      // label living inside the card — the same identity shape in every layout mode.
      group
        .append("rect")
        .attr("class", "d3-node-glyph d3-node-card")
        .attr("x", -cardWidth / 2)
        .attr("y", -metrics.height / 2)
        .attr("width", cardWidth)
        .attr("height", metrics.height)
        .attr("rx", metrics.radius)
        .attr("fill", palette.cardFill)
        .attr("stroke", palette.cardStroke)
        .attr("stroke-width", 1.2);
      group
        .append("rect")
        .attr("class", "d3-node-accent")
        .attr("x", -cardWidth / 2 + 1)
        .attr("y", -metrics.height / 2 + 1)
        .attr("width", metrics.accentWidth)
        .attr("height", metrics.height - 2)
        .attr("rx", 2)
        .attr("fill", color);

      // Keep compact cards easy to acquire with a mouse or touch. This transparent target is
      // deliberately larger than the painted card and bubbles interaction to the node group.
      group
        .append("rect")
        .attr("class", "d3-node-hit-target")
        .attr("x", -cardWidth / 2 - 6)
        .attr("y", -metrics.height / 2 - 6)
        .attr("width", cardWidth + 12)
        .attr("height", metrics.height + 12)
        .attr("rx", metrics.radius + 4)
        .attr("fill", "transparent")
        .attr("pointer-events", "all");

      if (relationship) {
        group
          .append("text")
          .attr("class", "d3-node-type-label")
          .attr("x", -cardWidth / 2 + 14)
          .attr("y", -5)
          .attr("font-size", "7.5px")
          .attr("font-weight", "800")
          .attr("letter-spacing", ".08em")
          .attr("fill", color)
          .text(visibleType);
      }
      group
        .append("text")
        .attr("class", "d3-node-label")
        .attr("x", -cardWidth / 2 + 14)
        .attr("y", relationship ? 12 : 4)
        .attr("font-size", "11px")
        .attr("font-weight", "700")
        .attr("fill", palette.labelText)
        .text(visibleLabel);
      group.append("title").text(`${d.label} · ${graphTypeLabel(d.type)}`);
    });

    nodesEnter.merge(nodes)
      .attr("data-node-type", (node) => node.type)
      .attr("aria-label", (node) => {
        if (hierarchy && isHierarchyBoard(node) && (node.child_count ?? 0) > 0) {
          return `${node.expanded_group ? hierarchyLabels.close : hierarchyLabels.open}: ${node.label}`;
        }
        if (hierarchy && ((node.collapsed_leaf_count ?? 0) > 0 || node.leaf_group_expanded)) {
          return `${node.leaf_group_expanded ? hierarchyLabels.close : hierarchyLabels.open}: ${node.label}`;
        }
        return `${node.type}: ${node.label}`;
      })
      .each(function (data) {
      const node = d3.select(this);
      node.select("title").text(`${data.label} · ${graphTypeLabel(data.type)}`);
      if (hierarchy) {
        const color = getNodeColor(data.type);
        const board = isHierarchyBoard(data);
        node.select(".d3-hierarchy-accent").attr("fill", color);
        node.select(".d3-hierarchy-type")
          .attr("fill", color)
          .text(graphTypeLabel(data.type).toUpperCase());
        node.select(".d3-node-label")
          .text(data.label.length > (data.expanded_group ? 46 : board ? 24 : 20)
            ? data.label.slice(0, data.expanded_group ? 46 : board ? 24 : 20) + "…"
            : data.label);
        node.select(".d3-hierarchy-child-count").text(String(data.child_count ?? 0));
        node.select(".d3-hierarchy-board-action")
          .text(boardFooter(data, Boolean(data.expanded_group), hierarchyLabels));
        return;
      }
      const color = getNodeColor(data.type);
      const visibleLabel = data.label.length > 26 ? data.label.slice(0, 26) + "…" : data.label;
      const visibleType = graphTypeLabel(data.type).toUpperCase();
      const metrics = nodeCardMetrics(visibleLabel, data.degree);
      const cardWidth = nodeCardWidth(data.label, data.degree, relationship ? visibleType : undefined);
      data.cardWidth = cardWidth;

      node.select(".d3-node-card")
        .attr("x", -cardWidth / 2)
        .attr("y", -metrics.height / 2)
        .attr("width", cardWidth)
        .attr("height", metrics.height)
        .attr("rx", metrics.radius)
        .attr("fill", palette.cardFill)
        .attr("stroke", palette.cardStroke);
      node.select(".d3-node-accent")
        .attr("x", -cardWidth / 2 + 1)
        .attr("y", -metrics.height / 2 + 1)
        .attr("width", metrics.accentWidth)
        .attr("height", metrics.height - 2)
        .attr("fill", color);
      node.select(".d3-node-hit-target")
        .attr("x", -cardWidth / 2 - 6)
        .attr("y", -metrics.height / 2 - 6)
        .attr("width", cardWidth + 12)
        .attr("height", metrics.height + 12);
      node.select(".d3-node-type-label")
        .attr("x", -cardWidth / 2 + 14)
        .attr("fill", color)
        .text(visibleType);
      node.select(".d3-node-label")
        .attr("x", -cardWidth / 2 + 14)
        .attr("fill", palette.labelText)
        .text(visibleLabel);
      });
    this.nodeElementById.clear();
    this.nodesGroup.selectAll<SVGGElement, D3Node>(".d3-node").each((node, index, elements) => {
      this.nodeElementById.set(node.id, elements[index]);
    });
  }

  private renderLabels() {
    this.labelsGroup.selectAll("*").remove();
    if (this.layoutMode === "relationship") {
      const types = [...new Set(this.nodes.map((node) => node.type))]
        .filter((type) => this.nodes.filter((node) => node.type === type).length > 1);
      this.labelsGroup
        .selectAll<SVGTextElement, string>("text.d3-community-label")
        .data(types)
        .enter()
        .append("text")
        .attr("class", "d3-community-label")
        .attr("data-community", (type) => type)
        .text((type) => `${graphTypeLabel(type)} · ${this.nodes.filter((node) => node.type === type).length}`);
      return;
    }

    const isSystemHierarchy = this.layoutMode === "hierarchy" &&
      this.nodes.some((node) => node.type === "SystemRoot") &&
      this.nodes.some((node) => node.type === "SystemPillar");
    if (!isSystemHierarchy) return;

    const overlays = this.labelsGroup
      .selectAll<SVGGElement, D3Node>("g.d3-system-label-overlay")
      .data(this.nodes, (node) => node.id)
      .enter()
      .append("g")
      .attr("class", "d3-system-label-overlay")
      .attr("data-node-id", (node) => node.id)
      .attr("aria-hidden", "true")
      .attr("pointer-events", "none")
      .attr("transform", (node) => `translate(${node.x ?? 0},${node.y ?? 0})`);

    overlays.each((node, index, elements) => {
      const source = this.nodeElementById.get(node.id);
      if (!source) return;
      const overlay = elements[index];
      source.querySelectorAll<SVGTextElement>(":scope > text").forEach((sourceText) => {
        const clone = sourceText.cloneNode(true) as SVGTextElement;
        clone.setAttribute("aria-hidden", "true");
        clone.removeAttribute("visibility");
        overlay.appendChild(clone);
        sourceText.setAttribute("visibility", "hidden");
      });
    });
  }

  private edgePathFor(edge: D3Edge): string {
    const source = typeof edge.source === "object" ? edge.source : this.nodeDataById.get(edge.source);
    const target = typeof edge.target === "object" ? edge.target : this.nodeDataById.get(edge.target);
    if (!source || !target) return "";
    const sourceX = source.x ?? 0;
    const sourceY = source.y ?? 0;
    const targetX = target.x ?? 0;
    const targetY = target.y ?? 0;
    if (this.layoutMode === "hierarchy") {
      if (!isHierarchyTreeEdge(edge)) {
        const startY = sourceY - hierarchyNodeHeight(source) / 2;
        const endY = targetY - hierarchyNodeHeight(target) / 2;
        const controlY = Math.min(startY, endY) - Math.min(90, Math.abs(targetX - sourceX) * .12 + 24);
        return `M ${sourceX} ${startY} C ${sourceX} ${controlY}, ${targetX} ${controlY}, ${targetX} ${endY}`;
      }
      return cardEdgePath(
        sourceX, sourceY, hierarchyNodeWidth(source),
        targetX, targetY, hierarchyNodeWidth(target),
      );
    }
    return facingCardEdgePath(
      sourceX, sourceY, source.cardWidth ?? 120,
      targetX, targetY, target.cardWidth ?? 120,
    );
  }

  private tick() {
    this.edgesGroup
      .selectAll<SVGPathElement, D3Edge>(".d3-edge")
      .attr("d", (d) => this.edgePathFor(d));

    this.nodesGroup
      .selectAll<SVGGElement, D3Node>(".d3-node")
      .attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    this.labelsGroup
      .selectAll<SVGGElement, D3Node>(".d3-system-label-overlay")
      .attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);

    if (this.layoutMode === "relationship") this.updateCommunityHalos();
  }

  private updateCommunityHalos(onlyType?: string) {
    const padding = 42;
    this.communitiesGroup.selectAll<SVGGElement, string>("g.d3-community").each((type, index, elements) => {
      if (onlyType && type !== onlyType) return;
      const members = this.nodes.filter((node) => node.type === type && node.x !== undefined && node.y !== undefined);
      if (members.length < 2) return;
      const minX = d3.min(members, (node) => node.x ?? 0) ?? 0;
      const maxX = d3.max(members, (node) => node.x ?? 0) ?? 0;
      const minY = d3.min(members, (node) => node.y ?? 0) ?? 0;
      const maxY = d3.max(members, (node) => node.y ?? 0) ?? 0;
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const radius = Math.max(70, Math.hypot(maxX - minX, maxY - minY) / 2 + padding);
      const group = d3.select(elements[index]);
      group.select("circle")
        .attr("cx", centerX)
        .attr("cy", centerY)
        .attr("r", radius)
        .attr("stroke", getNodeColor(type))
        .attr("fill", getNodeColor(type));
      this.labelsGroup
        .selectAll<SVGTextElement, string>("text.d3-community-label")
        .filter((labelType) => labelType === type)
        .attr("x", centerX)
        .attr("y", centerY - radius + 20)
        .attr("fill", getNodeColor(type));
    });
  }

  private boardChildren(board: D3Node): D3Node[] {
    if (!isHierarchyBoard(board) || !board.expanded_group) return [];
    const children = new Set<D3Node>();
    this.incidentEdges.get(board.id)?.forEach((id) => {
      const edge = this.edgeDataById.get(id);
      if (edge && isHierarchyEdgeType(edge.type) && edge.source === board && typeof edge.target === "object") {
        children.add(edge.target);
      }
    });
    return [...children];
  }

  private drag() {
    return d3.drag<SVGGElement, D3Node>()
      .touchable(false)
      .filter((event) => !this.activeDrag && !this.touchingCanvas &&
        !event.ctrlKey && !event.button && !this.isNodeAction(event.target))
      .on("start", (event, node) => {
        const drag = this.beginDrag(node, "mouse");
        event.on("drag", (move: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) => {
          if (this.activeDrag === drag) this.moveDrag(drag, move.x, move.y);
        });
        event.on("end", () => {
          if (this.activeDrag === drag) this.finishDrag();
        });
      });
  }

  private isNodeAction(target: EventTarget | null) {
    return target instanceof Element && Boolean(target.closest(".d3-hierarchy-leaf-action, .d3-hierarchy-port.output"));
  }

  private bindTouchDrag() {
    // Let D3 zoom receive the native second touch along with the first touch's
    // current location. Cancel the card move before D3 zoom takes over.
    this.svg
      .on("touchstart.pinch", (event: TouchEvent) => {
        if (event.touches.length < 2) return;
        this.touchingCanvas = true;
        if (typeof this.activeDrag?.identifier === "number") this.finishDrag(true, false);
      }, { capture: true })
      .on("touchend.pinch touchcancel.pinch", (event: TouchEvent) => {
        if (!this.touchingCanvas || event.touches.length) return;
        this.touchingCanvas = false;
        // D3 zoom still needs this touch-end event before we can replace the SVG targets.
        queueMicrotask(() => {
          if (this.svg.node()?.isConnected) this.flushDeferredDragUpdates();
        });
      }, { capture: true });

    this.nodesGroup
      .on("touchstart.card", (event: TouchEvent) => {
        if (this.touchingCanvas || this.activeDrag || this.isNodeAction(event.target)) return;
        const target = event.target instanceof Element && event.target.closest<SVGGElement>(".d3-node");
        const touch = event.changedTouches[0];
        if (!target || !touch) return;
        const node = d3.select<SVGGElement, D3Node>(target).datum();
        event.stopPropagation();
        this.beginDrag(node, touch.identifier, d3.pointer(touch, this.nodesGroup.node()));
      })
      .on("touchmove.card", (event: TouchEvent) => {
        const drag = this.activeDrag;
        if (!drag || drag.identifier === "mouse") return;
        const touch = Array.from(event.changedTouches).find((item) => item.identifier === drag.identifier);
        if (!touch) return;
        event.stopPropagation();
        event.preventDefault();
        const [x, y] = d3.pointer(touch, this.nodesGroup.node());
        this.moveDrag(drag, x + drag.pointerOffset[0], y + drag.pointerOffset[1]);
      }, { passive: false })
      .on("touchend.card touchcancel.card", (event: TouchEvent) => {
        const drag = this.activeDrag;
        if (!drag || !Array.from(event.changedTouches).some((touch) => touch.identifier === drag.identifier)) return;
        event.stopPropagation();
        this.finishDrag(event.type === "touchcancel");
      });
  }

  private beginDrag(node: D3Node, identifier: DragState["identifier"], point?: [number, number]): DragState {
    this.stopRelationshipLayout();
    this.svg.interrupt();
    const drag: DragState = {
      nodeId: node.id,
      identifier,
      pointerOffset: point ? [(node.x ?? 0) - point[0], (node.y ?? 0) - point[1]] : [0, 0],
      origins: [node, ...this.boardChildren(node)].map((item) => ({
        node: item,
        x: item.x ?? 0,
        y: item.y ?? 0,
        fx: item.fx,
        fy: item.fy,
      })),
      moved: false,
    };
    this.activeDrag = drag;
    return drag;
  }

  private moveDrag(drag: DragState, x: number, y: number) {
    const dx = x - drag.origins[0].x;
    const dy = y - drag.origins[0].y;
    if (!drag.moved && Math.hypot(dx, dy) < .01) return;
    if (!drag.moved) {
      drag.moved = true;
      this.nodeElementById.get(drag.nodeId)?.classList.add("d3-node-dragging");
      this.svg.classed("d3-dragging", true);
    }
    drag.origins.forEach((origin) => {
      origin.node.x = origin.x + dx;
      origin.node.y = origin.y + dy;
    });
    drag.origins.forEach(({ node }) => this.updateDraggedGeometry(node));
  }

  private finishDrag(cancelled = false, flush = true) {
    const drag = this.activeDrag;
    if (!drag) return;
    if (drag.moved) {
      drag.origins.forEach(({ node, x, y, fx, fy }) => {
        if (cancelled) {
          Object.assign(node, { x, y, fx, fy });
        } else if (node.id === drag.nodeId || fx != null || fy != null) {
          node.fx = node.x;
          node.fy = node.y;
        }
      });
      if (cancelled) drag.origins.forEach(({ node }) => this.updateDraggedGeometry(node));
    }
    this.nodeElementById.get(drag.nodeId)?.classList.remove("d3-node-dragging");
    this.svg.classed("d3-dragging", false);
    this.activeDrag = null;
    if (flush) this.flushDeferredDragUpdates();
  }

  private flushDeferredDragUpdates() {
    if (this.activeDrag || this.touchingCanvas) return;
    const data = this.pendingData;
    this.pendingData = null;
    if (data) {
      this.readTheme();
      this.setData(data.nodes, data.edges, false);
    } else {
      this.refreshTheme();
    }
    this.resize(false);
  }

  private updateDraggedGeometry(node: D3Node) {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const element = this.nodeElementById.get(node.id);
    element?.setAttribute("transform", `translate(${x},${y})`);
    const overlay = this.labelsGroup.select<SVGGElement>(`[data-node-id="${node.id}"]`);
    if (!overlay.empty()) overlay.attr("transform", `translate(${x},${y})`);
    (this.incidentEdges.get(node.id) ?? new Set<string>()).forEach((edgeId) => {
      const edge = this.edgeDataById.get(edgeId);
      const edgeElement = this.edgeElementById.get(edgeId);
      if (!edge || !edgeElement) return;
      edgeElement.setAttribute("d", this.edgePathFor(edge));
    });
    if (this.layoutMode === "relationship") this.updateCommunityHalos(node.type);
  }

  private updateSelection() {
    const selectedNodeId = this.selectedNodeId;
    const selectedEdgeId = this.selectedEdgeId;
    const hierarchy = this.layoutMode === "hierarchy";
    const palette = this.palette;

    this.nodesGroup.selectAll<SVGGElement, D3Node>(".d3-node").each(function (d) {
      const node = d3.select(this);
      const isSelected = d.id === selectedNodeId;
      if (hierarchy) {
        node.select(".d3-hierarchy-card")
          .attr("stroke", isSelected ? palette.cardStrokeSelected : palette.cardStroke)
          .attr("stroke-width", isSelected ? 2.5 : 1.5);
        return;
      }
      node.select(".d3-node-card")
        .attr("stroke", isSelected ? palette.cardStrokeSelected : palette.cardStroke)
        .attr("stroke-width", isSelected ? 2 : 1.2);
    });

    if (hierarchy) {
      this.updateHierarchyFocus();
      return;
    }

    this.edgesGroup.selectAll<SVGElement, D3Edge>(".d3-edge")
      .attr("stroke", (edge) => getEdgeColor(edge.type))
      .attr("opacity", (edge) => edge.id === selectedEdgeId ? 1 : .6)
      .attr("stroke-width", (edge) => edge.id === selectedEdgeId ? 3 : getEdgeWidth(edge.type));
    this.updateRelationshipFocus();
    this.updateOrbitLabels();
  }

  private updateHover() {
    const hoveredNodeId = this.hoveredNodeId;
    const hierarchy = this.layoutMode === "hierarchy";

    if (!hierarchy) {
      // Relationship hover stays bounded to the already-indexed incident edge set. It never
      // toggles corpus-wide focus or scans every edge, which keeps the large SVG cheap to paint.
      if (this.layoutMode === "relationship") this.updateRelationshipHoverEdges(hoveredNodeId);
      return;
    }

    this.updateHierarchyHoverEdges(hoveredNodeId);
  }

  private updateHierarchyFocus() {
    if (this.layoutMode !== "hierarchy") return;
    const focusId = this.selectedNodeId;
    this.edgesGroup.selectAll<SVGPathElement, D3Edge>(".d3-edge")
      .interrupt()
      .attr("stroke", (edge) => {
        if (!isHierarchyTreeEdge(edge)) return getEdgeColor(edge.type);
        return edge.id === this.selectedEdgeId ? "url(#d3-hierarchy-edge-active)" : "url(#d3-hierarchy-edge)";
      })
      .attr("opacity", (edge) => {
        if (edge.id === this.selectedEdgeId || edge.id === this.hoveredEdgeId) return 1;
        const structural = isHierarchyTreeEdge(edge);
        if (!focusId) return structural ? .72 : .1;
        const safe = graphEdge(edge);
        const incident = safe.source === focusId || safe.target === focusId;
        if (incident) return structural ? .92 : .88;
        return structural ? .24 : .02;
      })
      .attr("stroke-width", (edge) => {
        if (edge.id === this.selectedEdgeId || edge.id === this.hoveredEdgeId) return 3;
        const safe = graphEdge(edge);
        const incident = focusId && (safe.source === focusId || safe.target === focusId);
        if (incident) return isHierarchyTreeEdge(edge) ? 2.3 : 1.8;
        return isHierarchyTreeEdge(edge) ? 1.8 : 1.15;
      });
  }

  private updateRelationshipFocus() {
    if (this.layoutMode === "hierarchy") return;
    const focusId = this.selectedNodeId;
    if (focusId === this.appliedRelationshipFocusId) return;
    this.clearRelationshipFocusClasses();
    this.appliedRelationshipFocusId = focusId;
    this.svg.classed("d3-relationship-focused", Boolean(focusId));
    const projection = relationshipFocusProjection(
      focusId,
      this.adjacency,
      this.incidentEdges,
      this.relationshipLabelRanks,
    );
    if (!projection.focusId) return;

    const focusElement = this.nodeElementById.get(projection.focusId);
    focusElement?.classList.add("d3-focus-node");
    this.appliedFocusNodeIds.add(projection.focusId);
    projection.neighborNodeIds.forEach((nodeId) => {
      this.nodeElementById.get(nodeId)?.classList.add("d3-focus-neighbor");
      this.appliedFocusNodeIds.add(nodeId);
    });
    projection.incidentEdgeIds.forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.add("d3-focus-edge");
      this.appliedFocusEdgeIds.add(edgeId);
    });
  }

  private updateRelationshipHoverEdges(focusId: string | null) {
    this.clearRelationshipHoverEdges();
    if (this.layoutMode !== "relationship" || !focusId) return;
    (this.incidentEdges.get(focusId) ?? new Set<string>()).forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.add("d3-hover-edge");
      this.appliedHoverEdgeIds.add(edgeId);
    });
  }

  private updateHierarchyHoverEdges(focusId: string | null) {
    this.clearHierarchyHoverEdges();
    if (this.layoutMode !== "hierarchy" || !focusId) return;
    (this.incidentEdges.get(focusId) ?? new Set<string>()).forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.add("d3-hierarchy-hover-edge");
      this.appliedHierarchyHoverEdgeIds.add(edgeId);
    });
  }

  private clearHierarchyHoverEdges() {
    this.appliedHierarchyHoverEdgeIds.forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.remove("d3-hierarchy-hover-edge");
    });
    this.appliedHierarchyHoverEdgeIds.clear();
  }

  private clearRelationshipHoverEdges() {
    this.appliedHoverEdgeIds.forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.remove("d3-hover-edge");
    });
    this.appliedHoverEdgeIds.clear();
  }

  private clearRelationshipFocusClasses() {
    this.appliedFocusNodeIds.forEach((nodeId) => {
      this.nodeElementById.get(nodeId)?.classList.remove(
        "d3-focus-node",
        "d3-focus-neighbor",
        "d3-focus-label",
      );
    });
    this.appliedFocusEdgeIds.forEach((edgeId) => {
      this.edgeElementById.get(edgeId)?.classList.remove("d3-focus-edge");
    });
    this.appliedFocusNodeIds.clear();
    this.appliedFocusEdgeIds.clear();
    this.appliedRelationshipFocusId = null;
    this.svg.classed("d3-relationship-focused", false);
  }

  private updateOrbitLabels() {
    if (this.layoutMode !== "orbit") return;
    const budget = Math.min(10, relationshipLabelBudget(this.nodes.length, this.currentZoom));
    const visible = (node: D3Node) => (this.relationshipLabelRanks.get(node.id) ?? Infinity) < budget;

    this.nodesGroup.selectAll<SVGGElement, D3Node>(".d3-node").each(function (node) {
      const opacity = visible(node) ? 1 : 0;
      d3.select(this).selectAll<SVGElement, D3Node>(".d3-node-label, .d3-node-label-backdrop")
        .attr("opacity", opacity);
    });
  }

  zoomIn() {
    this.svg.transition().duration(300).call(this.zoomBehavior.scaleBy, 1.3);
  }

  zoomOut() {
    this.svg.transition().duration(300).call(this.zoomBehavior.scaleBy, 0.77);
  }

  fitToScreen(animate = true) {
    const bounds = this.container.node()?.getBBox();
    if (!bounds) return;

    // The guide and status bar are part of the usable viewport. Fit into the unobscured area,
    // including scales below the normal wheel-zoom floor when a complete overview requires it.
    const insets = this.layoutMode === "hierarchy"
      ? { top: 96, right: 32, bottom: 54, left: 32 }
      : { top: 40, right: 40, bottom: 54, left: 40 };
    const fitted = graphFitTransform(bounds, this.width, this.height, insets);
    const transform = d3.zoomIdentity.translate(fitted.x, fitted.y).scale(fitted.scale);
    if (animate) {
      this.svg
        .transition()
        .duration(500)
        .call(this.zoomBehavior.transform, transform);
      return;
    }
    this.svg.interrupt().call(this.zoomBehavior.transform, transform);
  }

  private openHierarchyAtReadableScale() {
    if (this.layoutMode !== "hierarchy" || this.nodes.length <= 36) {
      this.fitToScreen();
      return;
    }
    const scale = this.width < 680 ? .62 : .78;
    const leftInset = this.width < 680 ? 18 : 38;
    const targetIds = new Set(this.edges.map((edge) => graphEdge(edge).target));
    const anchor = this.nodes
      .filter((node) => !targetIds.has(node.id))
      .sort((left, right) =>
        (right.child_count ?? right.degree) - (left.child_count ?? left.degree) ||
        left.label.localeCompare(right.label),
      )[0];
    if (!anchor) {
      this.fitToScreen();
      return;
    }
    const anchorX = anchor.x ?? 0;
    const anchorY = anchor.y ?? 0;
    const verticalCenter = this.height * (this.width < 680 ? .54 : .58);
    this.svg.call(
      this.zoomBehavior.transform,
      d3.zoomIdentity
        .translate(leftInset - (anchorX - hierarchyNodeWidth(anchor) / 2) * scale, verticalCenter - anchorY * scale)
        .scale(scale),
    );
  }

  relayout() {
    // Auto-arrange: free-drag placements are released and the deterministic layout
    // for the current mode takes over again.
    if (this.activeDrag) this.finishDrag();
    this.nodes.forEach((node) => {
      node.fx = null;
      node.fy = null;
    });
    if (this.layoutMode === "hierarchy") {
      this.applyHierarchyPositions();
      this.tick();
      this.openHierarchyAtReadableScale();
      return;
    }
    if (this.layoutMode === "orbit") {
      this.applyOrbitPositions();
      this.renderCommunities();
      this.tick();
      this.fitToScreen();
      return;
    }
    this.settleRelationshipLayout(110, 1);
  }

  resize(fit = true) {
    if (this.activeDrag) return;
    const rect = this.containerElement.getBoundingClientRect();
    if (!dimensionsChanged(
      { width: this.width, height: this.height },
      { width: rect.width, height: rect.height },
    )) return;
    this.width = rect.width;
    this.height = rect.height;
    this.svg.attr("width", this.width).attr("height", this.height);
    if (this.layoutMode === "hierarchy") {
      this.applyHierarchyPositions();
      this.tick();
      // A viewport resize is an explicit screen-fit event. Initial data still opens at a readable
      // panning scale, while resize keeps every rendered card on the newly available canvas.
      if (fit) this.fitToScreen(false);
      return;
    }
    if (this.layoutMode === "orbit") {
      this.applyOrbitPositions();
      this.renderCommunities();
      this.tick();
      if (fit) this.fitToScreen();
      return;
    }
    this.configureForces();
    this.settleRelationshipLayout(48, .42, fit);
  }

  destroy() {
    this.finishDrag(true, false);
    this.pendingData = null;
    this.simulation.stop();
    this.clearHierarchyHoverEdges();
    this.themeObserver?.disconnect();
    this.themeObserver = null;
    if (this.themeMedia && this.onThemeMediaChange) {
      this.themeMedia.removeEventListener?.("change", this.onThemeMediaChange);
    }
    this.themeMedia = null;
    this.onThemeMediaChange = null;
    this.svg.remove();
  }

  getZoom(): number {
    return d3.zoomTransform(this.svg.node()!).k;
  }
}
