import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import DocumentWorkspaceDetail from "./page";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "workspace-1" }) }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    if (queryKey[0] === "document-workspace-content") {
      return {
        isLoading: false,
        error: null,
        data: {
          workspace_id: "workspace-1", filename: "agents.md", format: "md",
          preview_kind: "markdown", source_text: "# Governed agents",
          extracted_text: "Governed agents", supports_raw: true, source_truncated: false,
        },
      };
    }
    if (queryKey[0] === "document-workspace-graph") {
      return {
        data: {
          workspace_id: "workspace-1",
          nodes: [{
            id: "node-1", node_type: "claim", label: "Grounded claim",
            summary: "The document states that explicit human approval and traceable evidence improve the reliability of governed business-agent decisions before graph publication.",
            parent_node_id: null, confidence: 0.9, evidence_status: "supported",
            evidence: [{ id: "ev-1", location: { section_heading: "Methods" }, excerpt: "Human approval improves reliability.", extraction_method: "ai-extraction" }],
            ai_research: {
              research_summary: "Independent AI research also identifies bounded actions and durable operational memory as necessary controls for reliable governed agents.",
              comparison_status: "different",
              difference_summary: "The source omits bounded-action controls that independent AI research considers material.",
              confidence: 0.82, provider_name: "mistral", model_name: "mistral-large-latest",
              prompt_version: "v1", researched_at: "2026-08-09T00:00:00Z",
            },
          }],
          edges: [], meta: { node_count: 1, edge_count: 0 },
        },
      };
    }
    return {
      isLoading: false,
      refetch: vi.fn(),
      data: {
        id: "workspace-1", research_id: "research-1", attachment_id: "attachment-1",
        filename: "agents.md", mime_type: "text/markdown", size_bytes: 100,
        content_hash: "a".repeat(64), processing_status: "needs_review",
        review_status: "needs_review", extraction_limitations: [], error_code: null,
        error_message: null, provider_name: "mistral", model_name: "mistral-large-latest",
        attempt_count: 1, next_attempt_at: null, started_at: null, finished_at: null,
        extracted_char_count: 1200, graph_node_count: 1, graph_edge_count: 0,
        evaluation: {
          id: "evaluation-1", rubric_version: "v1", fit_score: 77.75,
          decision: "draft_graph", failed_gates: [], matched_pillars: ["Agent System Architecture"],
          candidate_parents: [], contribution_types: [], overlaps_with: [], fills_gaps: [],
          limitations: [], reasoning_summary: "Grounded assessment", confidence: 0.9,
          provider_name: "mistral", model_name: "mistral-large-latest", prompt_version: "v1",
          dimension_scores: { system_fit: 85 }, created_at: "2026-07-18T00:00:00Z",
        },
        created_at: "2026-07-18T00:00:00Z", updated_at: "2026-07-18T00:00:00Z",
      },
    };
  },
}));

it("shows paper fit, graph nodes and grounded evidence", () => {
  render(<DocumentWorkspaceDetail />);

  expect(screen.getByText("77.75")).toBeInTheDocument();
  expect(screen.getByText("sourceAndPreview")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Grounded claim" }));
  expect(screen.getByText("Human approval improves reliability.")).toBeInTheDocument();
  expect(screen.getByText(/bounded-action controls/)).toBeInTheDocument();
  expect(screen.getByText("aiComparisonDifferent")).toBeInTheDocument();
});
