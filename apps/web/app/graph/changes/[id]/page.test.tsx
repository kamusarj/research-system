import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import GraphChangeSetDetail from "./page";
import { changeSetAction } from "@/lib/graph-changes";
import type { GraphChangeSet } from "@/lib/types";

const refetch = vi.fn().mockResolvedValue(undefined);

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "change-set-1" }) }));
vi.mock("@/lib/graph-changes", () => ({
  changeSetAction: vi.fn(),
  decideGraphMutation: vi.fn(),
}));
vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    isLoading: false,
    refetch,
    data: {
      id: "change-set-1",
      origin_type: "document_workspace",
      origin_id: "workspace-1",
      title: "Map Agent Memory paper",
      summary: "Review ontology proposals",
      lifecycle_status: "needs_review",
      validation_summary: { valid_count: 2, warning_count: 1, error_count: 0 },
      created_by: "system",
      approved_by: null,
      applied_at: null,
      mutations: [],
      created_at: "2026-07-18T00:00:00Z",
      updated_at: "2026-07-18T00:00:00Z",
    },
  }),
}));

it("shows validation metrics and approves the reviewed change set", async () => {
  vi.mocked(changeSetAction).mockResolvedValue({ id: "change-set-1" } as GraphChangeSet);
  render(<GraphChangeSetDetail />);

  expect(screen.getByText("Map Agent Memory paper")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "approveAll" }));

  await waitFor(() => expect(changeSetAction).toHaveBeenCalledWith(
    "change-set-1",
    "approve",
  ));
  expect(refetch).toHaveBeenCalledOnce();
});
