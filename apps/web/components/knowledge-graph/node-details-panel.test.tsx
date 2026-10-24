import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { NodeDetailsPanel } from "./node-details-panel";

vi.mock("@/hooks/use-ontology-node", () => ({
  useOntologyNode: () => ({
    children: {
      isLoading: false,
      error: null,
      data: [
        {
          id: "child",
          canonical_label: "Child concept",
          child_count: 2,
        },
      ],
    },
    breadcrumb: { data: [] },
  }),
}));

const node = {
  id: "root",
  type: "SystemRoot",
  label: "Business AI Agents",
  summary: "Canonical root",
  confidence: 1,
  source_count: 0,
  published: true,
  degree: 1,
  child_count: 1,
  lifecycle_status: "approved",
  provenance: { created_by_type: "migration" },
};

it("shows hierarchy children and provenance in node detail tabs", () => {
  const onBrowseNode = vi.fn();
  render(
    <NodeDetailsPanel
      node={node}
      relationships={[]}
      ontologyBacked
      view="hierarchy"
      inCurrentView
      expanding={false}
      onExpand={vi.fn()}
      onHide={vi.fn()}
      onBrowseNode={onBrowseNode}
    />,
  );

  expect(screen.getByText("Gốc hệ thống")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "detailTab.children" }));
  fireEvent.click(screen.getByRole("button", { name: /Child concept/ }));
  expect(onBrowseNode).toHaveBeenCalledWith("child");

  fireEvent.click(screen.getByRole("tab", { name: "detailTab.provenance" }));
  expect(screen.getByText("migration")).toBeInTheDocument();
  expect(screen.getByText("status.approved")).toBeInTheDocument();
});
