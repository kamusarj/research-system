# Graph Intelligence v2 Evaluation Report

Date: 2026-07-18  
Fixture: `paper-fit-gold-v1`  
Scope: deterministic release regression for routing, canonical-pillar candidate placement and
near-duplicate detection.

## Result

| Metric | Target | Result | Status |
|---|---:|---:|---|
| Priority/draft routing precision | >= 0.85 | 1.00 | Pass |
| Top-three ontology placement recall | >= 0.85 | 1.00 | Pass |
| Near-duplicate recall | >= 0.90 | 1.00 | Pass |
| Near-duplicate precision | tracked | 1.00 | Pass |
| Fixture schema failure rate | < 0.01 | 0.00 | Pass |

The fixture contains 30 examples: 10 core, 10 enabling, 5 tangential and 5 irrelevant. It includes
strong-method/low-business, strong-business/weak-evidence, foundational, recent implementation and
one labeled near-duplicate pair.

## What was evaluated

- Server-owned weighted paper-fit scoring and routing boundaries.
- A deterministic canonical-pillar resolver that validates provider labels and adds keyword-based
  fallback candidates. The same resolver now runs in document processing.
- A title-plus-dimension near-duplicate detector. Detected candidates are recorded in
  `overlaps_with` and remain human-reviewed; they do not auto-merge or publish.
- Pydantic parsing of every fixture record.

Run the report again with:

```bash
make evaluate-graph-v2
```

## Interpretation limits

This is a versioned regression set, not evidence of general-world model accuracy. It deliberately
measures deterministic server behavior independently of provider availability. The provider schema
failure metric above is fixture parsing, not a production traffic rate; production invalid-output,
latency, cost and mutation acceptance rates must be monitored from real audited sessions before a
broad rollout. Prompt/rubric semantics were not changed because the accepted fixture thresholds
already pass.

## Governance checks

- Paper evaluation still produces reviewable document state only.
- Placement fallback cannot write canonical nodes or edges.
- Near-duplicate detection adds review context only.
- Chat/document proposals still require change-set validation, approval and explicit apply.
