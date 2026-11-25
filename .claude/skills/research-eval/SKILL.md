---
name: research-eval
description: Run the research agent evaluation set (8 Business AI Agents questions) for the reference and optimized pipeline variants and compare speed, AI calls, tokens and report quality. Use when evaluating or benchmarking the research pipeline, or when asked for /research-eval.
---

# Research eval

Measures the research pipeline with real model and search calls, so it spends AI quota: about
5–12 provider calls per question and variant. Say how many questions will run before starting
and run a subset (`--questions q1-market-size,q3-platform-comparison`) unless a full run was
asked for.

## Steps

1. Follow `docs/evaluations/research-agent/README.md`. Use a separate, migrated evaluation database
   and the same frozen corpus for both variants. Keep the corpus outside the repository.
2. From `apps/api`, run the reference variant first and proceed to the optimized variant only
   after the reference command succeeds:

   ```bash
   export DATABASE_URL="${RESEARCH_EVAL_DATABASE_URL:?Set the isolated evaluation database URL}" &&
   uv run --frozen python -m app.operations research-eval \
     --variant reference --corpus /tmp/research-public-corpus.json \
     --stop-on-provider-error --output /tmp/research-eval-reference.json &&
   uv run --frozen python -m app.operations research-eval \
     --variant optimized --corpus /tmp/research-public-corpus.json \
     --stop-on-provider-error --output /tmp/research-eval-optimized.json
   ```

   Pass the same `--questions` filter to both commands for a diagnostic subset.
3. Compare:

   ```bash
   uv run --frozen python -m app.operations research-eval-compare \
     /tmp/research-eval-reference.json /tmp/research-eval-optimized.json
   ```

4. Report the table and any quality gate failures. A subset or stopped run is diagnostic evidence;
   only the full set can qualify for the token KPI.
   Copy the JSON files to `docs/evaluations/research-agent/` only if asked to keep them.

Metric definitions live in `apps/api/app/evaluation/research_agent.py`; the questions in
`apps/api/app/evaluation/research_eval_v1.json`.
