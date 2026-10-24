import * as d3 from "d3";
import type { GraphEdge, GraphLayoutMode, GraphNode } from "./types";
import { buildHierarchyLayout } from "./hierarchy-layout";
import {
  rankRelationshipLabels,
  relationshipLabelBudget,
  isHierarchyEdgeType,
} from "./graph-visualization";
import {
  getNodeColor,
  getEdgeColor,
  getNodeShape,
  getNodeRadius,
  getEdgeWidth,
  getEdgeDash,
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
    hierarchyX?: number;
    hierarchyY?: number;
    hierarchyWidth?: number;
    hierarchyHeight?: number;
  };
type D3Edge = Omit<GraphEdge, "source" | "target"> &
  d3.SimulationLinkDatum<D3Node> & {
    source: string | D3Node;
    target: string | D3Node;
  };

const HIERARCHY_NODE_WIDTH = 184;
const HIERARCHY_NODE_HEIGHT = 64;
const HIERARCHY_BOARD_HEIGHT = 76;
const HIERARCHY_LIST_NODE_WIDTH = 156;
const HIERARCHY_LIST_NODE_HEIGHT = 48;

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
  const source = typeof edge.source === "object" ? edge.source.id : String(edge.source);
  const target = typeof edge.target === "object" ? edge.target.id : String(edge.target);
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
  private relationshipLabelRanks = new Map<string, number>();
  private adjacency = new Map<string, Set<string>>();
  private incidentEdges = new Map<string, Set<string>>();
  private nodeElementById = new Map<string, SVGGElement>();
  private edgeElementById = new Map<string, SVGElement>();
  private appliedRelationshipFocusId: string | null = null;
  private appliedFocusNodeIds = new Set<string>();
  private appliedFocusEdgeIds = new Set<string>();
  private appliedHoverEdgeIds = new Set<string>();
  private appliedHierarchyHoverEdgeIds = new Set<string>();
  private currentZoom = 1;
  private callbacks: D3GraphCallbacks;
  private lastTap = { id: "", at: 0 };
  private layoutMode: GraphLayoutMode = "relationship";
  private labelsVisible = true;
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

    this.svg = d3
      .select(this.containerElement)
      .append("svg")
      .attr("width", this.width)
      .attr("height", this.height)
      .attr("class", "d3-graph-svg");

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
    arrow.append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "#9bb0b8");

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

    const relGradient = defs.append("radialGradient")
      .attr("id", "d3-relationship-node")
      .attr("cx", "35%").attr("cy", "30%").attr("r", "75%");
    relGradient.append("stop").attr("offset", "0%").attr("stop-color", "#ffffff").attr("stop-opacity", "0.4");
    relGradient.append("stop").attr("offset", "100%").attr("stop-color", "#0d2d3a").attr("stop-opacity", "0");

    this.communitiesGroup = this.container.append("g").attr("class", "d3-communities");
    this.edgesGroup = this.container.append("g").attr("class", "d3-edges");
    this.nodesGroup = this.container.append("g").attr("class", "d3-nodes");
    this.labelsGroup = this.container.append("g").attr("class", "d3-labels");

    this.zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.05, 4])
      .on("zoom", (event) => {
        this.currentZoom = event.transform.k;
        this.container.attr("transform", event.transform);
        this.updateRelationshipLabels();
        this.callbacks.onZoomChange(this.currentZoom);
      });

    this.svg.call(this.zoomBehavior);

    this.svg.on("click", (event) => {
      if (event.target === this.svg.node()) {
        this.callbacks.onClearSelection();
        this.selectedNodeId = null;
        this.selectedEdgeId = null;
        this.updateSelection();
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
  }

  setLayoutMode(mode: GraphLayoutMode) {
    if (this.layoutMode === mode) return;
    this.simulation.stop();
    this.clearRelationshipHoverEdges();
    this.clearHierarchyHoverEdges();
    this.clearRelationshipFocusClasses();
    this.layoutMode = mode;
    this.edgesGroup.selectAll("*").remove();
    this.nodesGroup.selectAll("*").remove();
    this.communitiesGroup.selectAll("*").remove();
    this.configureForces();
  }

  setLabelsVisible(visible: boolean) {
    this.labelsVisible = visible;
    this.updateRelationshipLabels();
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
      .force("collision", d3.forceCollide<D3Node>().radius((d) => getNodeRadius(d.type, d.degree) + 10).iterations(2))
      .force("x", d3.forceX<D3Node>((node) => anchors.get(node.type)?.x ?? this.width / 2).strength(.19))
      .force("y", d3.forceY<D3Node>((node) => anchors.get(node.type)?.y ?? this.height / 2).strength(.19))
      .alphaDecay(0.04);
  }

  private applyOrbitPositions() {
    if (this.layoutMode !== "orbit") return;
    const centerX = this.width / 2;
    const centerY = this.height / 2;
    const ranked = [...this.nodes].sort((left, right) =>
      right.degree - left.degree ||
      right.source_count - left.source_count ||
      left.type.localeCompare(right.type) ||
      left.label.localeCompare(right.label),
    );
    const count = Math.max(1, ranked.length);
    const ringGroups: D3Node[][] = [[], [], [], []];
    ranked.forEach((node, index) => {
      const ratio = index / count;
      const ring = ratio < .04 ? 0 : ratio < .2 ? 1 : ratio < .55 ? 2 : 3;
      ringGroups[ring].push(node);
    });
    const maxRadius = Math.max(150, Math.min(this.width, this.height) * .43);
    const radii = [Math.min(52, maxRadius * .12), maxRadius * .4, maxRadius * .7, maxRadius];
    ringGroups.forEach((group, ring) => {
      group
        .sort((left, right) => left.type.localeCompare(right.type) || left.label.localeCompare(right.label))
        .forEach((node, index) => {
          const angle = -Math.PI / 2 + (index / Math.max(1, group.length)) * Math.PI * 2;
          const stagger = ring === 0 ? 0 : ((index % 3) - 1) * Math.min(16, radii[ring] * .05);
          node.x = centerX + Math.cos(angle) * (radii[ring] + stagger);
          node.y = centerY + Math.sin(angle) * (radii[ring] + stagger);
          node.fx = node.x;
          node.fy = node.y;
        });
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
      node.x = node.hierarchyX;
      node.y = node.hierarchyY;
    });
  }

  setData(nodes: GraphNode[], edges: GraphEdge[]) {
    this.clearRelationshipHoverEdges();
    this.clearHierarchyHoverEdges();
    this.clearRelationshipFocusClasses();
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
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
      if (this.layoutMode !== "relationship") {
        return {
          ...n,
          x: this.nodes.find((existing) => existing.id === n.id)?.x ?? this.width / 2,
          y: this.nodes.find((existing) => existing.id === n.id)?.y ?? this.height / 2,
        };
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
    this.edges = edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        ...e,
        source: this.layoutMode === "hierarchy" ? renderedNodeMap.get(e.source)! : e.source,
        target: this.layoutMode === "hierarchy" ? renderedNodeMap.get(e.target)! : e.target,
      }) as unknown as D3Edge);

    this.relationshipLabelRanks = rankRelationshipLabels(this.nodes);
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

    this.render();
    this.updateSelection();
    this.updateRelationshipLabels();
    if (this.layoutMode === "hierarchy" || this.layoutMode === "orbit") {
      this.simulation.stop();
      this.tick();
      if (this.layoutMode === "hierarchy") this.openHierarchyAtReadableScale();
      else this.fitToScreen();
      return;
    }
    this.settleRelationshipLayout(90, .72);
  }

  private settleRelationshipLayout(iterations: number, alpha: number) {
    if (this.layoutMode !== "relationship") return;
    this.simulation.alpha(alpha).alphaTarget(0).stop().tick(iterations);
    this.tick();
    this.fitToScreen(false);
  }

  private render() {
    this.renderCommunities();
    this.renderEdges();
    this.renderNodes();
    this.renderLabels();
  }

  private renderCommunities() {
    this.communitiesGroup.selectAll("*").remove();
    if (this.layoutMode === "hierarchy") return;
    if (this.layoutMode === "orbit") {
      const maxRadius = Math.max(150, Math.min(this.width, this.height) * .43);
      [Math.min(52, maxRadius * .12), maxRadius * .4, maxRadius * .7, maxRadius].forEach((radius, index) => {
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

  private renderEdges() {
    const hierarchy = this.layoutMode === "hierarchy";
    if (hierarchy) {
      this.edgesGroup.selectAll("*").remove();
      const edges = this.edgesGroup
        .selectAll<SVGPathElement, D3Edge>("path.d3-edge")
        .data(this.edges, (d) => d.id);
      edges.exit().remove();
      edges
        .enter()
        .append("path")
        .attr("class", (d) => isHierarchyEdgeType(d.type)
          ? "d3-edge d3-hierarchy-edge"
          : "d3-edge d3-hierarchy-relation-edge")
        .attr("data-edge-id", (d) => d.id)
        .attr("display", (d) => {
          const source = d.source as D3Node;
          return source.expanded_group ? "none" : null;
        })
        .attr("fill", "none")
        .attr("stroke", (d) => isHierarchyEdgeType(d.type)
          ? (d.id === this.selectedEdgeId ? "url(#d3-hierarchy-edge-active)" : "url(#d3-hierarchy-edge)")
          : getEdgeColor(d.type))
        .attr("stroke-width", (d) => isHierarchyEdgeType(d.type) ? 1.8 : 1.15)
        .attr("stroke-linecap", "round")
        .attr("stroke-dasharray", (d) => isHierarchyEdgeType(d.type) ? getEdgeDash(d.type) : "4 5")
        .attr("opacity", (d) => isHierarchyEdgeType(d.type) ? 0.72 : 0.1)
        .attr("marker-end", (d) => isHierarchyEdgeType(d.type) ? null : "url(#arrowhead)")
        .on("click", (event, d) => {
          event.stopPropagation();
          this.callbacks.onEdgeSelect(graphEdge(d));
          this.selectedEdgeId = d.id;
          this.selectedNodeId = null;
          this.updateSelection();
        })
        .on("mouseenter", (event, d) => {
          (event.currentTarget as SVGElement).classList.add("d3-edge-hovered");
          this.hoveredEdgeId = d.id;
          this.updateHover();
        })
        .on("mouseleave", (event) => {
          (event.currentTarget as SVGElement).classList.remove("d3-edge-hovered");
          this.hoveredEdgeId = null;
          this.updateHover();
        });
    } else {
      const edges = this.edgesGroup
        .selectAll<SVGLineElement, D3Edge>("line.d3-edge")
        .data(this.edges, (d) => d.id);
      edges.exit().remove();
      edges
        .enter()
        .append("line")
        .attr("class", this.layoutMode === "relationship"
          ? "d3-edge d3-network-edge"
          : "d3-edge d3-orbit-edge")
        .attr("stroke", (d) => getEdgeColor(d.type))
        .attr("stroke-width", (d) => getEdgeWidth(d.type))
        .attr("stroke-dasharray", (d) => getEdgeDash(d.type))
        .attr("opacity", 0.6)
        .attr("marker-end", "url(#arrowhead)")
        .on("click", (event, d) => {
          event.stopPropagation();
          this.callbacks.onEdgeSelect(graphEdge(d));
          this.selectedEdgeId = d.id;
          this.selectedNodeId = null;
          this.updateSelection();
        })
        .on("mouseenter", (event, d) => {
          (event.currentTarget as SVGElement).classList.add("d3-edge-hovered");
          this.hoveredEdgeId = d.id;
          this.updateHover();
        })
        .on("mouseleave", (event) => {
          (event.currentTarget as SVGElement).classList.remove("d3-edge-hovered");
          this.hoveredEdgeId = null;
          this.updateHover();
        });
    }

    this.edgesGroup.selectAll<SVGElement, D3Edge>(".d3-edge")
      .attr("stroke", (d) => hierarchy
        ? isHierarchyEdgeType(d.type)
          ? (d.id === this.selectedEdgeId ? "url(#d3-hierarchy-edge-active)" : "url(#d3-hierarchy-edge)")
          : getEdgeColor(d.type)
        : getEdgeColor(d.type))
      .attr("stroke-width", (d) => hierarchy ? isHierarchyEdgeType(d.type) ? 1.8 : 1.15 : getEdgeWidth(d.type))
      .attr("stroke-dasharray", (d) => hierarchy && !isHierarchyEdgeType(d.type) ? "4 5" : getEdgeDash(d.type));
    this.edgeElementById.clear();
    this.edgesGroup.selectAll<SVGElement, D3Edge>(".d3-edge").each((edge, index, elements) => {
      this.edgeElementById.set(edge.id, elements[index]);
    });
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
      .attr("aria-label", (d) => hierarchy && isHierarchyBoard(d)
        ? `${d.expanded_group ? this.hierarchyLabels.close : this.hierarchyLabels.open}: ${d.label}`
        : hierarchy && ((d.collapsed_leaf_count ?? 0) > 0 || d.leaf_group_expanded)
          ? `${d.leaf_group_expanded ? this.hierarchyLabels.close : this.hierarchyLabels.open}: ${d.label}`
        : `${d.type}: ${d.label}`)
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
        this.selectedNodeId = d.id;
        this.selectedEdgeId = null;
        this.updateSelection();
      })
      .on("keydown", (event, d) => {
        if (!["Enter", " "].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        this.callbacks.onNodeSelect(d);
        this.selectedNodeId = d.id;
        this.selectedEdgeId = null;
        this.updateSelection();
        // Enter opens a node that has somewhere to go; on a leaf it simply selects,
        // matching what a click does.
        const canOpen = this.layoutMode === "hierarchy"
          ? (d.child_count ?? 0) > 0 || (d.collapsed_leaf_count ?? 0) > 0 || Boolean(d.leaf_group_expanded)
          : (d.degree ?? 0) > 0;
        if (canOpen) this.callbacks.onExpandNode(d.id);
      })
      .on("focus", (event, d) => {
        (event.currentTarget as SVGGElement).classList.add("d3-node-hovered");
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
        (event.currentTarget as SVGGElement).classList.remove("d3-node-hovered");
        this.hoveredNodeId = null;
        this.updateHover();
      });

    if (this.layoutMode === "relationship") nodesEnter.call(this.drag());
    const callbacks = this.callbacks;
    const hierarchyLabels = this.hierarchyLabels;
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
          .attr("fill", expandedBoard ? "#f5f3ff" : board ? "#f8f7ff" : "#ffffff")
          .attr("stroke", "#d8e0ea")
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
          .attr("fill", "#172033")
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
            .attr("fill", "#5969d8")
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
      const shape = getNodeShape(d.type);
      const radius = getNodeRadius(d.type, d.degree);
      const color = getNodeColor(d.type);

      if (shape === "rect") {
        group
          .append("rect")
          .attr("x", -radius * 1.2)
          .attr("y", -radius * 0.9)
          .attr("width", radius * 2.4)
          .attr("height", radius * 1.8)
          .attr("rx", 4)
          .attr("fill", color)
          .attr("stroke", "#fff")
          .attr("stroke-width", 1.5);
        group
          .append("rect")
          .attr("class", "d3-node-sheen")
          .attr("x", -radius * 1.2)
          .attr("y", -radius * 0.9)
          .attr("width", radius * 2.4)
          .attr("height", radius * 1.8)
          .attr("rx", 4)
          .attr("fill", "url(#d3-relationship-node)")
          .attr("pointer-events", "none");
      } else if (shape === "diamond") {
        group
          .append("path")
          .attr("class", "d3-node-glyph")
          .attr("d", `M 0 ${-radius} L ${radius} 0 L 0 ${radius} L ${-radius} 0 Z`)
          .attr("fill", color)
          .attr("stroke", "#fff")
          .attr("stroke-width", 1.5);
      } else {
        group
          .append("circle")
          .attr("class", "d3-node-glyph")
          .attr("r", radius)
          .attr("fill", color)
          .attr("stroke", "#fff")
          .attr("stroke-width", 1.5);
        group
          .append("circle")
          .attr("class", "d3-node-sheen")
          .attr("r", radius)
          .attr("fill", "url(#d3-relationship-node)")
          .attr("pointer-events", "none");
      }

      // Keep compact glyphs easy to acquire with a mouse or touch. This transparent target is
      // deliberately larger than the painted node and bubbles interaction to the node group.
      group
        .append("circle")
        .attr("class", "d3-node-hit-target")
        .attr("r", Math.max(22, radius))
        .attr("fill", "transparent")
        .attr("pointer-events", "all");

      const visibleLabel = d.label.length > 28 ? `${d.label.slice(0, 28)}…` : d.label;
      const visibleType = graphTypeLabel(d.type).toUpperCase();
      const labelWidth = Math.min(
        196,
        Math.max(52, visibleLabel.length * 6.2 + 18, relationship ? visibleType.length * 5.4 + 18 : 0),
      );
      group
        .append("rect")
        .attr("class", "d3-node-label-backdrop")
        .attr("x", -labelWidth / 2)
        .attr("y", radius + 6)
        .attr("width", labelWidth)
        .attr("height", relationship ? 38 : 22)
        .attr("rx", relationship ? 9 : 11)
        .attr("fill", "rgba(255,255,255,.96)")
        .attr("stroke", "rgba(99,102,241,.22)")
        .attr("stroke-width", .75);
      if (relationship) {
        group
          .append("text")
          .attr("class", "d3-node-type-label")
          .attr("text-anchor", "middle")
          .attr("y", radius + 18)
          .attr("font-size", "7.5px")
          .attr("font-weight", "800")
          .attr("letter-spacing", ".08em")
          .attr("fill", color)
          .text(visibleType);
      }
      group
        .append("text")
        .attr("class", "d3-node-label")
        .attr("text-anchor", "middle")
        .attr("dy", radius + (relationship ? 34 : 22))
        .attr("font-size", "10.5px")
        .attr("font-weight", "700")
        .attr("fill", "#263247")
        .text(visibleLabel);
    });

    this.nodesGroup.selectAll(".d3-node").each(function (d) {
      const node = d3.select(this);
      const data = d as D3Node;
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
      const radius = getNodeRadius(data.type, data.degree);
      const shape = getNodeShape(data.type);
      const color = getNodeColor(data.type);

      if (shape === "rect") {
        node.select(".d3-node-glyph")
          .attr("x", -radius * 1.2)
          .attr("y", -radius * 0.9)
          .attr("width", radius * 2.4)
          .attr("height", radius * 1.8)
          .attr("fill", color);
        node.select(".d3-node-sheen")
          .attr("x", -radius * 1.2)
          .attr("y", -radius * 0.9)
          .attr("width", radius * 2.4)
          .attr("height", radius * 1.8);
      } else if (shape === "diamond") {
        node.select(".d3-node-glyph")
          .attr("d", `M 0 ${-radius} L ${radius} 0 L 0 ${radius} L ${-radius} 0 Z`)
          .attr("fill", color);
      } else {
        node.select(".d3-node-glyph")
          .attr("r", radius)
          .attr("fill", color);
        node.select(".d3-node-sheen").attr("r", radius);
      }

      const visibleLabel = data.label.length > 28 ? data.label.slice(0, 28) + "…" : data.label;
      const visibleType = graphTypeLabel(data.type).toUpperCase();
      const labelWidth = Math.min(
        196,
        Math.max(52, visibleLabel.length * 6.2 + 18, relationship ? visibleType.length * 5.4 + 18 : 0),
      );
      node.select(".d3-node-label-backdrop")
        .attr("x", -labelWidth / 2)
        .attr("y", radius + 6)
        .attr("width", labelWidth)
        .attr("height", relationship ? 38 : 22)
        .attr("rx", relationship ? 9 : 11);
      node.select(".d3-node-type-label")
        .attr("y", radius + 18)
        .attr("fill", color)
        .text(visibleType);
      node.select(".d3-node-label")
        .attr("dy", radius + (relationship ? 34 : 22))
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

  private tick() {
    if (this.layoutMode === "hierarchy") {
      this.edgesGroup
        .selectAll<SVGPathElement, D3Edge>(".d3-edge")
        .attr("d", (d) => {
          const source = d.source as D3Node;
          const target = d.target as D3Node;
          if (!isHierarchyEdgeType(d.type)) {
            const sourceX = source.x ?? 0;
            const sourceY = source.y ?? 0;
            const targetX = target.x ?? 0;
            const targetY = target.y ?? 0;
            const midpointX = (sourceX + targetX) / 2;
            const midpointY = Math.min(sourceY, targetY) - Math.min(90, Math.abs(targetX - sourceX) * .12 + 24);
            return `M ${sourceX} ${sourceY} Q ${midpointX} ${midpointY}, ${targetX} ${targetY}`;
          }
          const sourceX = (source.x ?? 0) + hierarchyNodeWidth(source) / 2;
          const sourceY = source.y ?? 0;
          const targetX = (target.x ?? 0) - hierarchyNodeWidth(target) / 2;
          const targetY = target.y ?? 0;
          const midpoint = sourceX + (targetX - sourceX) / 2;
          return `M ${sourceX} ${sourceY} C ${midpoint} ${sourceY}, ${midpoint} ${targetY}, ${targetX} ${targetY}`;
        });
    } else {
      this.edgesGroup
        .selectAll<SVGLineElement, D3Edge>(".d3-edge")
        .attr("x1", (d) => (d.source as D3Node).x ?? 0)
        .attr("y1", (d) => (d.source as D3Node).y ?? 0)
        .attr("x2", (d) => (d.target as D3Node).x ?? 0)
        .attr("y2", (d) => (d.target as D3Node).y ?? 0);
    }

    this.nodesGroup
      .selectAll<SVGGElement, D3Node>(".d3-node")
      .attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    this.labelsGroup
      .selectAll<SVGGElement, D3Node>(".d3-system-label-overlay")
      .attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);

    if (this.layoutMode === "relationship") this.updateCommunityHalos();
  }

  private updateCommunityHalos() {
    const padding = 42;
    this.communitiesGroup.selectAll<SVGGElement, string>("g.d3-community").each((type, index, elements) => {
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

  private drag() {
    return d3
      .drag<SVGGElement, D3Node>()
      .on("start", (event, d) => {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) this.simulation.alphaTarget(0).stop();
        d.fx = null;
        d.fy = null;
      });
  }

  private updateSelection() {
    const selectedNodeId = this.selectedNodeId;
    const selectedEdgeId = this.selectedEdgeId;
    const hierarchy = this.layoutMode === "hierarchy";

    this.nodesGroup.selectAll<SVGGElement, D3Node>(".d3-node").each(function (d) {
      const node = d3.select(this);
      const isSelected = d.id === selectedNodeId;
      if (hierarchy) {
        node.select(".d3-hierarchy-card")
          .attr("stroke", isSelected ? "#6366f1" : "#d8e0ea")
          .attr("stroke-width", isSelected ? 2.5 : 1.5);
        return;
      }
      node.select(".d3-node-glyph")
        .attr("stroke", isSelected ? "#a5b4fc" : "#dbeafe")
        .attr("stroke-width", isSelected ? 3 : 1.5);
    });

    this.edgesGroup.selectAll<SVGElement, D3Edge>(".d3-edge").each(function (d) {
      const edge = d3.select(this);
      const isSelected = d.id === selectedEdgeId;
      edge
        .attr("opacity", isSelected ? 1 : hierarchy ? isHierarchyEdgeType(d.type) ? .72 : .1 : 0.6)
        .attr("stroke-width", isSelected ? 3 : hierarchy ? isHierarchyEdgeType(d.type) ? 1.8 : 1.15 : getEdgeWidth(d.type));
    });
    if (!hierarchy) {
      this.updateRelationshipFocus();
      this.updateRelationshipLabels();
    } else this.updateHierarchyFocus();
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
      .attr("opacity", (edge) => {
        if (edge.id === this.selectedEdgeId || edge.id === this.hoveredEdgeId) return 1;
        const structural = isHierarchyEdgeType(edge.type);
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
        if (incident) return isHierarchyEdgeType(edge.type) ? 2.3 : 1.8;
        return isHierarchyEdgeType(edge.type) ? 1.8 : 1.15;
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

  private updateRelationshipLabels() {
    if (this.layoutMode === "hierarchy") return;
    if (this.layoutMode === "relationship") {
      // Network labels follow one predictable rule: hidden at rest and revealed only by the
      // local hover/focus class. Importance still controls glyph size, never overview labels.
      this.nodesGroup.selectAll<SVGGElement, D3Node>(".d3-node").each(function () {
        d3.select(this).selectAll<SVGElement, D3Node>(".d3-node-type-label, .d3-node-label, .d3-node-label-backdrop")
          .attr("opacity", 0);
      });
      return;
    }
    const budget = this.layoutMode === "orbit"
      ? Math.min(10, relationshipLabelBudget(this.nodes.length, this.currentZoom))
      : relationshipLabelBudget(this.nodes.length, this.currentZoom);
    const visible = (node: D3Node) =>
      this.labelsVisible && (this.relationshipLabelRanks.get(node.id) ?? Infinity) < budget;

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

  resize() {
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
      this.fitToScreen(false);
      return;
    }
    if (this.layoutMode === "orbit") {
      this.applyOrbitPositions();
      this.renderCommunities();
      this.tick();
      this.fitToScreen();
      return;
    }
    this.configureForces();
    this.settleRelationshipLayout(48, .42);
  }

  destroy() {
    this.simulation.stop();
    this.clearHierarchyHoverEdges();
    this.svg.remove();
  }

  getZoom(): number {
    return d3.zoomTransform(this.svg.node()!).k;
  }
}
