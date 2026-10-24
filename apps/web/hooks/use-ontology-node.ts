"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getOntologyBreadcrumb,
  getOntologyChildren,
} from "@/lib/knowledge-graph/ontology-api";

export function useOntologyNode(nodeId: string | undefined, enabled = true) {
  const active = Boolean(nodeId) && enabled;
  const children = useQuery({
    queryKey: ["ontology-children", nodeId],
    queryFn: () => getOntologyChildren(nodeId!),
    enabled: active,
  });
  const breadcrumb = useQuery({
    queryKey: ["ontology-breadcrumb", nodeId],
    queryFn: () => getOntologyBreadcrumb(nodeId!),
    enabled: active,
  });
  return { children, breadcrumb };
}
