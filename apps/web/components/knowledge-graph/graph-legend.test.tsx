import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GraphLegend } from "./graph-legend";
import { LocaleProvider } from "@/lib/i18n";
import { graphTypeLabel } from "@/lib/knowledge-graph/graph-theme";

describe("GraphLegend", () => {
  it("names node types in the reader's language, not in the data model's", () => {
    render(
      <LocaleProvider>
        <GraphLegend counts={{ SystemPillar: 11, ResearchItem: 3 }} />
      </LocaleProvider>,
    );

    expect(screen.getByText("Trụ cột hệ thống")).toBeInTheDocument();
    expect(screen.getByText("Hồ sơ nghiên cứu")).toBeInTheDocument();
    expect(screen.queryByText("SystemPillar")).not.toBeInTheDocument();
  });

  it("covers both graph vocabularies from one component", () => {
    render(
      <LocaleProvider>
        {/* Hierarchy types and relationship types side by side. */}
        <GraphLegend counts={{ Concept: 4, Person: 2 }} />
      </LocaleProvider>,
    );

    expect(screen.getByText("Khái niệm")).toBeInTheDocument();
    expect(screen.getByText("Tác giả")).toBeInTheDocument();
  });

  it("says so when nothing is on the canvas", () => {
    render(
      <LocaleProvider>
        <GraphLegend counts={{}} />
      </LocaleProvider>,
    );

    expect(screen.getByText("Không có loại nút nào hiển thị trong chế độ này.")).toBeInTheDocument();
  });
});

describe("graphTypeLabel", () => {
  it("falls back to a readable form for a type with no translation", () => {
    expect(graphTypeLabel("SomeFutureNodeType")).toBe("Some Future Node Type");
  });

  it("prefers a supplied translation", () => {
    expect(graphTypeLabel("Concept", { Concept: "Khái niệm" })).toBe("Khái niệm");
  });
});
