import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunProgress } from "./run-progress";
import type { ResearchRun } from "@/lib/research-runs";

const run = {
  id: "r1", question: "q", status: "running", stage: "extracting", variant: "optimized", provider_name: null,
  model_name: null, knowledge_gap_id: null, report_research_id: null, error_code: null, error_message: null,
  metrics: { queries_planned: 10, sources_discovered: 18, sources_ready: 12 }, created_by: "u",
  created_at: "2026-10-24T00:00:00Z", started_at: null, finished_at: null,
} satisfies ResearchRun;

describe("RunProgress", () => {
  it("shows per-stage counts, the current step and announces the latest event", () => {
    render(<RunProgress run={run} events={[{ id: 3, kind: "progress", stage: "extracting", message: "Đã trích nhận định từ 4 nguồn, còn 8 nguồn.", data: {}, created_at: "" }]} />);
    expect(screen.getByText("10 truy vấn")).toBeInTheDocument();
    expect(screen.getByText("12 nguồn đọc được")).toBeInTheDocument();
    expect(screen.getByText("Trích nhận định").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("status")).toHaveTextContent("còn 8 nguồn");
  });
});
