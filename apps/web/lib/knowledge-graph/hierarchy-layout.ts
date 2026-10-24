import type { GraphEdge, GraphNode } from "./types";

export type HierarchyPosition = {
  x: number;
  y: number;
  depth: number;
  width?: number;
  height?: number;
};

const HIERARCHY_EDGE_TYPES = new Set(["PARENT_OF", "BROADER_THAN"]);

export function buildHierarchyLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
): Map<string, HierarchyPosition> {
  const safeWidth = Math.max(width, 760);
  const safeHeight = Math.max(height, 420);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const children = new Map<string, string[]>();
  const incoming = new Map(nodes.map((node) => [node.id, 0]));

  edges.forEach((edge) => {
    if (
      !HIERARCHY_EDGE_TYPES.has(edge.type) ||
      !nodeById.has(edge.source) ||
      !nodeById.has(edge.target)
    ) {
      return;
    }
    children.set(edge.source, [...(children.get(edge.source) ?? []), edge.target]);
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
  });

  const byLabel = (left: string, right: string) =>
    (nodeById.get(left)?.label ?? left).localeCompare(nodeById.get(right)?.label ?? right);
  children.forEach((items, parentId) => children.set(parentId, [...new Set(items)].sort(byLabel)));

  const roots = nodes
    .filter((node) => (incoming.get(node.id) ?? 0) === 0)
    .map((node) => node.id)
    .sort(byLabel);
  const orderedRoots = roots.length > 0
    ? roots
    : nodes.map((node) => node.id).sort(byLabel);

  const openedBoard = nodes.find(
    (node) => node.type === "SystemPillar" && node.expanded_group,
  );
  if (openedBoard && (children.get(openedBoard.id)?.length ?? 0) > 0) {
    const boardChildren = [...(children.get(openedBoard.id) ?? [])].sort(byLabel);
    const columns = boardChildren.length > 22 ? 3 : boardChildren.length > 8 ? 2 : 1;
    const rows = Math.ceil(boardChildren.length / columns);
    const childWidth = 156;
    const childHeight = 48;
    const childColumnGap = 18;
    const childRowGap = 14;
    const groupPaddingX = 24;
    const groupPaddingTop = 22;
    const groupPaddingBottom = 22;
    const groupHeaderHeight = 64;
    const boardWidth = Math.max(
      420,
      groupPaddingX * 2 + columns * childWidth + Math.max(0, columns - 1) * childColumnGap,
    );
    const boardHeight =
      groupHeaderHeight +
      groupPaddingTop +
      rows * childHeight +
      Math.max(0, rows - 1) * childRowGap +
      groupPaddingBottom;
    const positions = new Map<string, HierarchyPosition>();
    const systemRoot = nodes.find((node) => node.type === "SystemRoot");
    const boardIds = (systemRoot ? children.get(systemRoot.id) ?? [] : [])
      .filter((id) => nodeById.get(id)?.type === "SystemPillar")
      .sort(byLabel);
    const visibleBoardIds = boardIds.length > 0
      ? boardIds
      : nodes
        .filter((node) => node.type === "SystemPillar")
        .map((node) => node.id)
        .sort(byLabel);
    const boardIndex = Math.max(0, visibleBoardIds.indexOf(openedBoard.id));
    const boardGap = 88;
    const listStartY = 60;
    const openedSlotY = listStartY + boardIndex * boardGap;
    const verticalOffset = Math.max(0, boardHeight / 2 + 30 - openedSlotY);
    const rootY =
      listStartY +
      verticalOffset +
      Math.max(0, visibleBoardIds.length - 1) * boardGap / 2;
    const collapsedBoardX = 320;
    const openedBoardLeft = 454;
    const openedBoardX = openedBoardLeft + boardWidth / 2;
    const openedBoardY = openedSlotY + verticalOffset;

    if (systemRoot) {
      positions.set(systemRoot.id, { x: 104, y: rootY, depth: 0 });
    }
    visibleBoardIds.forEach((id, index) => {
      if (id === openedBoard.id) return;
      positions.set(id, {
        x: collapsedBoardX,
        y: listStartY + verticalOffset + index * boardGap,
        depth: 1,
      });
    });
    positions.set(openedBoard.id, {
      x: openedBoardX,
      y: openedBoardY,
      depth: 1,
      width: boardWidth,
      height: boardHeight,
    });

    const childrenStartX = openedBoardLeft + groupPaddingX + childWidth / 2;
    const childrenStartY =
      openedBoardY -
      boardHeight / 2 +
      groupHeaderHeight +
      groupPaddingTop +
      childHeight / 2;
    boardChildren.forEach((id, index) => {
      const column = Math.floor(index / rows);
      const row = index % rows;
      positions.set(id, {
        x: childrenStartX + column * (childWidth + childColumnGap),
        y: childrenStartY + row * (childHeight + childRowGap),
        depth: 2,
      });
    });

    nodes
      .map((node) => node.id)
      .filter((id) => !positions.has(id))
      .sort(byLabel)
      .forEach((id, index) => {
        positions.set(id, {
          x: collapsedBoardX,
          y: listStartY + verticalOffset + (visibleBoardIds.length + index) * boardGap,
          depth: 1,
        });
      });
    return positions;
  }

  // A shallow research forest is not one tall taxonomy. Packing dozens of independent roots into
  // a single vertical lane creates kilometres of whitespace and forces fit-to-screen to shrink
  // every card. Arrange those independent one-hop branches as a stable masonry atlas instead.
  const shallowForest =
    orderedRoots.length > 6 &&
    nodes.every((node) => (incoming.get(node.id) ?? 0) === 0 || (children.get(node.id)?.length ?? 0) === 0);
  if (shallowForest) {
    const positions = new Map<string, HierarchyPosition>();
    const columnCount = safeWidth >= 1100 ? 4 : safeWidth >= 820 ? 3 : 2;
    const branchWidth = 430;
    const branchGapY = 26;
    const rootX = 86;
    const childX = 310;
    const childGapY = 62;
    const columnHeights = Array.from({ length: columnCount }, () => 28);
    const stableRoots = [...orderedRoots].sort((left, right) => {
      const childDelta = (children.get(right)?.length ?? 0) - (children.get(left)?.length ?? 0);
      return childDelta || byLabel(left, right);
    });

    stableRoots.forEach((rootId) => {
      const branchChildren = children.get(rootId) ?? [];
      const branchHeight = Math.max(82, branchChildren.length * childGapY + 20);
      const column = columnHeights.indexOf(Math.min(...columnHeights));
      const top = columnHeights[column];
      const originX = column * branchWidth;
      positions.set(rootId, {
        x: originX + rootX,
        y: top + branchHeight / 2,
        depth: 0,
      });
      branchChildren.forEach((childId, index) => {
        positions.set(childId, {
          x: originX + childX,
          y: top + 20 + index * childGapY + childGapY / 2,
          depth: 1,
        });
      });
      columnHeights[column] += branchHeight + branchGapY;
    });
    return positions;
  }

  const rawPositions = new Map<string, HierarchyPosition>();
  const visited = new Set<string>();
  const verticalGap = 82;
  let leafIndex = 0;

  function placeBranch(id: string, depth: number): number {
    if (visited.has(id)) return rawPositions.get(id)?.y ?? leafIndex * verticalGap;
    visited.add(id);
    const branchChildren = (children.get(id) ?? []).filter((childId) => !visited.has(childId));
    const childY = branchChildren.map((childId) => placeBranch(childId, depth + 1));
    const y = childY.length > 0
      ? (childY[0] + childY[childY.length - 1]) / 2
      : leafIndex++ * verticalGap;
    rawPositions.set(id, { x: 0, y, depth });
    return y;
  }

  orderedRoots.forEach((id, index) => {
    if (index > 0 && leafIndex > 0) leafIndex += 0.65;
    placeBranch(id, 0);
  });
  nodes
    .map((node) => node.id)
    .filter((id) => !visited.has(id))
    .sort(byLabel)
    .forEach((id) => {
      if (leafIndex > 0) leafIndex += 0.65;
      placeBranch(id, 0);
    });

  const maxDepth = Math.max(0, ...[...rawPositions.values()].map((position) => position.depth));
  const horizontalPadding = 116;
  const verticalPadding = 72;
  const availableWidth = safeWidth - horizontalPadding * 2;
  const depthGap = maxDepth === 0
    ? 0
    : Math.max(220, Math.min(280, availableWidth / maxDepth));
  const rawY = [...rawPositions.values()].map((position) => position.y);
  const minY = Math.min(0, ...rawY);
  const maxY = Math.max(0, ...rawY);
  const contentHeight = maxY - minY;
  const yOffset = Math.max(verticalPadding, (safeHeight - contentHeight) / 2) - minY;
  const positions = new Map<string, HierarchyPosition>();

  rawPositions.forEach((position, id) => {
    positions.set(id, {
      x: horizontalPadding + position.depth * depthGap,
      y: position.y + yOffset,
      depth: position.depth,
    });
  });

  return positions;
}
