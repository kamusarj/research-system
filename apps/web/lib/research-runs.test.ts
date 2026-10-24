import { describe, expect, it } from "vitest";
import { citationIndex, isTerminal, STAGE_STEPS, stepStates, type ResearchRunClaim, type ResearchRunSource } from "./research-runs";

const source = (id: string, citation: number | null): ResearchRunSource => ({
  id, provider: "searxng", perspective: "market", url: `https://${id}.example`, domain: `${id}.example`,
  title: id, status: "ready", suspicious: false, citation_index: citation, error_code: null,
});
const claim = (id: string, sourceId: string, used: boolean): ResearchRunClaim => ({
  id, source_id: sourceId, perspective: "market", text: id, quote: "q", matched_quote: "q",
  match_method: "exact", entailment: "supported", status: "verified", reason: null, used_in_report: used,
});

describe("research run helpers", () => {
  it("marks earlier stages done, the current one running and later ones pending", () => {
    expect(stepStates({ stage: "fetching", status: "running" })).toEqual(["done", "done", "current", "pending", "pending", "pending"]);
    expect(stepStates({ stage: "verifying", status: "failed" })[4]).toBe("failed");
    expect(stepStates({ stage: "done", status: "completed" }).every((state) => state === "done")).toBe(true);
    expect(STAGE_STEPS).toHaveLength(6);
  });

  it("maps citation numbers to their source and only the claims used in the report", () => {
    const map = citationIndex({
      sources: [source("a", 2), source("b", null), source("c", 1)],
      claims: [claim("x", "a", true), claim("y", "a", false), claim("z", "c", true)],
    });
    expect([...map.keys()].sort()).toEqual([1, 2]);
    expect(map.get(2)?.claims.map((item) => item.id)).toEqual(["x"]);
    expect(map.get(1)?.source.id).toBe("c");
  });

  it("knows terminal statuses", () => {
    expect(isTerminal("completed")).toBe(true);
    expect(isTerminal("running")).toBe(false);
  });
});
