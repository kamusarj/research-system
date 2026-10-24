import { api } from "@/lib/api";
import type { OntologyNode } from "./types";

export function getOntologyRoots() {
  return api<OntologyNode[]>("/ontology/roots");
}

export function getOntologyChildren(nodeId: string) {
  return api<OntologyNode[]>(`/ontology/nodes/${encodeURIComponent(nodeId)}/children`);
}

export function getOntologyBreadcrumb(nodeId: string) {
  return api<OntologyNode[]>(`/ontology/nodes/${encodeURIComponent(nodeId)}/breadcrumb`);
}

/**
 * Find canonical nodes anywhere in the tree, not only in the branch on screen.
 *
 * Filtering the current view hides non-matches but cannot reveal a match that lives three
 * levels down, which made search useless for exactly the case it is needed for.
 */
export function searchOntology(query: string, limit = 12) {
  return api<OntologyNode[]>(
    `/ontology/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
}
