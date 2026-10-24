import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { GraphChangeReview } from "./graph-change-review";
import { decideGraphMutation } from "@/lib/graph-changes";
import type { GraphMutation } from "@/lib/types";

vi.mock("@/lib/graph-changes", () => ({ decideGraphMutation: vi.fn() }));

const mutation: GraphMutation = {
  id: "mutation-1",
  mutation_order: 0,
  operation: "CREATE_NODE",
  target_kind: "knowledge_node",
  target_id: "new-node-1",
  before_json: {},
  proposed_json: {
    canonical_label: "Agent Memories",
    node_type: "Concept",
    primary_parent_id: "parent-1",
    candidates: [{
      node_id: "canonical-1",
      canonical_label: "Agent Memory",
      node_type: "Concept",
      primary_parent_id: "parent-1",
      matched_by: "similarity",
      score: 0.92,
    }],
  },
  validation_status: "warning",
  validation_messages: [{
    level: "warning",
    code: "SIMILAR_CANDIDATE",
    message: "Review the similar canonical candidate before creating a node.",
  }],
  review_decision: "pending",
  reviewed_by: null,
  created_at: "2026-07-18T00:00:00Z",
  updated_at: "2026-07-18T00:00:00Z",
};

it("shows a candidate diff and saves the reviewed proposal", async () => {
  vi.mocked(decideGraphMutation).mockResolvedValue(mutation);
  const onChanged = vi.fn().mockResolvedValue(undefined);
  render(
    <GraphChangeReview
      changeSetId="change-set-1"
      mutation={mutation}
      editable
      onChanged={onChanged}
    />,
  );

  expect(screen.getByText("Agent Memory")).toBeInTheDocument();
  expect(screen.getByText("92%")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("canonicalLabel"), {
    target: { value: "Agent Long-Term Memory" },
  });
  fireEvent.click(screen.getByRole("button", { name: "acceptMutation" }));

  await waitFor(() => expect(decideGraphMutation).toHaveBeenCalledWith(
    "change-set-1",
    "mutation-1",
    "accepted",
    expect.objectContaining({ canonical_label: "Agent Long-Term Memory" }),
  ));
  expect(onChanged).toHaveBeenCalledOnce();
});

it("rejects a mutation without sending an edited proposal", async () => {
  vi.mocked(decideGraphMutation).mockResolvedValue(mutation);
  render(
    <GraphChangeReview
      changeSetId="change-set-1"
      mutation={mutation}
      editable
      onChanged={vi.fn().mockResolvedValue(undefined)}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "rejectMutation" }));

  await waitFor(() => expect(decideGraphMutation).toHaveBeenCalledWith(
    "change-set-1",
    "mutation-1",
    "rejected",
    undefined,
  ));
});
