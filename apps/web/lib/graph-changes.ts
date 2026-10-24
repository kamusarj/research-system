import { api } from "@/lib/api";
import type { GraphChangeSet, GraphMutation } from "@/lib/types";

export function createDocumentChangeSet(workspaceId: string): Promise<GraphChangeSet> {
  return api(`/documents/${workspaceId}/create-change-set`, { method: "POST" });
}

export function changeSetAction(
  changeSetId: string,
  action: "validate" | "approve" | "reject" | "apply" | "compensate",
): Promise<GraphChangeSet> {
  return api(`/graph/change-sets/${changeSetId}/${action}`, { method: "POST" });
}

export function decideGraphMutation(
  changeSetId: string,
  mutationId: string,
  decision: "accepted" | "rejected",
  proposedJson?: Record<string, unknown>,
): Promise<GraphMutation> {
  return api(`/graph/change-sets/${changeSetId}/mutations/${mutationId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, proposed_json: proposedJson }),
  });
}
