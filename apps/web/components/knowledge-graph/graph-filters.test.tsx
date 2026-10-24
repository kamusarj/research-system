import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GraphFilters } from "./graph-filters";
import { defaultGraphFilters } from "@/hooks/use-knowledge-graph";

const labels = {
  filters: "Filters",
  nodeTypes: "Node types",
  sources: "Sources",
  confidence: "Confidence",
  time: "Time range",
};

function renderFilters(view: "hierarchy" | "relationship") {
  return render(
    <GraphFilters
      filters={{ ...defaultGraphFilters }}
      nodeTypes={["SystemPillar", "ResearchItem"]}
      view={view}
      onChange={vi.fn()}
      labels={labels}
    />,
  );
}

describe("GraphFilters", () => {
  it("offers source, confidence and date filters where they mean something", () => {
    renderFilters("relationship");

    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("Confidence")).toBeInTheDocument();
    expect(screen.getByText("Time range")).toBeInTheDocument();
  });

  it("hides filters the hierarchy cannot act on", () => {
    renderFilters("hierarchy");

    // Canonical ontology nodes carry no source type, collection date or classifier
    // confidence, so these controls could only ever empty the view.
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
    expect(screen.queryByText("Confidence")).not.toBeInTheDocument();
    expect(screen.queryByText("Time range")).not.toBeInTheDocument();
    expect(screen.getByText("Node types")).toBeInTheDocument();
  });

  it("shows node types in a readable form", () => {
    renderFilters("hierarchy");

    expect(screen.getByText("Trụ cột hệ thống")).toBeInTheDocument();
  });
});
