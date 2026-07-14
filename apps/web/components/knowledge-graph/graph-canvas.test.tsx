import { render } from "@testing-library/react";
import { expect, it, vi } from "vitest";

const core = vi.hoisted(() => ({
  on: vi.fn(),
  batch: vi.fn((callback: () => void) => callback()),
  elements: vi.fn(() => []),
  getElementById: vi.fn(() => ({ length: 0 })),
  add: vi.fn(),
  layout: vi.fn(() => ({ run: vi.fn() })),
  nodes: vi.fn(() => ({ toggleClass: vi.fn() })),
  zoom: vi.fn(() => 1),
  resize: vi.fn(),
  fit: vi.fn(),
  removeAllListeners: vi.fn(),
  destroy: vi.fn(),
}));

vi.mock("cytoscape", () => ({ default: vi.fn(() => core) }));

import { GraphCanvas } from "./graph-canvas";

it("destroys the Cytoscape instance and listeners on unmount", () => {
  const view = render(
    <GraphCanvas
      nodes={[]}
      edges={[]}
      layoutNonce={0}
      fitNonce={0}
      onNodeSelect={vi.fn()}
      onEdgeSelect={vi.fn()}
      onClearSelection={vi.fn()}
      onExpandNode={vi.fn()}
    />,
  );
  view.unmount();
  expect(core.removeAllListeners).toHaveBeenCalledOnce();
  expect(core.destroy).toHaveBeenCalledOnce();
});
