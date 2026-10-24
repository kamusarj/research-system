# 0040 Document Knowledge Graph and Separate System Map

Date: 2026-08-09

## Status

Accepted

## Context

The document pipeline already creates isolated graphs, but only for sources scoring at least 60.
Node inspection has source evidence without independent AI comparison, and promotion requires a
separate change-set action. Meanwhile relationship represents approved research while hierarchy
represents the Business AI Agents ontology, so switching layouts changes the underlying dataset.
The owner requires complete document analysis, an AI research/promotion option, relationship and
hierarchy parity, no 100-item display cap and preservation of the system graph in a separate area.

## Decision

Every supported upload with readable canonical text receives an isolated document graph regardless
of paper-fit score. Paper-fit continues to inform routing and promotion review but no longer decides
whether analysis exists. Source-grounded node summaries are normalized to approximately 150–200
characters. Optional independent AI research is stored on derived nodes with typed consistency or
difference output and provider provenance.

AI research may create or reuse a draft document-origin graph change set, but cannot approve, apply,
publish or delete canonical data. Existing human review and transactional apply remain mandatory.

Relationship and hierarchy become two layouts over the same approved knowledge corpus. The browser
requests up to the configured 1,000-node operational ceiling so there is no fixed 100-item display
cap. The complete canonical Business AI Agents ontology remains a separate read-only system map.

This supersedes only the score-60 automatic document-graph construction default in DEC-018 and the
earlier plan. It does not weaken evidence, review, object storage, source versioning, graph
validation or canonical PostgreSQL ownership.

## Alternatives Considered

1. Let AI publish directly. Rejected because it bypasses human-reviewed change sets.
2. Keep the score gate and offer analysis only for high-fit documents. Rejected because isolated
   low-fit graphs do not contaminate canonical knowledge and are still useful for comparison.
3. Keep ontology hierarchy as the relationship layout's hierarchy. Rejected because switching views
   then changes corpus rather than layout.
4. Remove all graph bounds. Rejected because resource bounds are still required; the accepted change
   removes the 100-item product cap and raises the explicit operational ceiling to 1,000.

## Consequences

Positive:

- Every readable upload has useful, isolated analysis.
- Source facts and independent AI knowledge are visibly distinguished.
- Promotion stays explicit, validated and reversible.
- Relationship/hierarchy stay synchronized while the system ontology remains accessible.

Tradeoffs:

- Low-fit document processing incurs one additional bounded graph extraction call.
- Optional AI research incurs provider cost and reflects model knowledge rather than guaranteed live
  web research; the UI must label provenance and uncertainty honestly.
- A 1,000-node safety ceiling is suitable for the current local corpus but large deployments will
  eventually need cursor/tile loading.

## Follow-Up

- Add live-search/tool-backed research only through a separately accepted provider and citation
  contract.
- Add cursor/tile graph loading before the approved corpus approaches 1,000 visible nodes.
