---
name: research-eval
description: Run the research agent evaluation set (8 Business AI Agents questions) for the naive and optimized pipeline variants and compare speed, AI calls, tokens, citation coverage, quote verification, duplicate sources and perspective coverage. Use when changing the research pipeline, prompts, search providers or models and someone asks to evaluate, benchmark or compare before/after, or types /research-eval.
---

# Research eval

Measures the research pipeline with real model and search calls, so it spends AI quota: about
5–12 provider calls per question and variant. Say how many questions will run before starting
and run a subset (`--questions q1-market-size,q3-platform-comparison`) unless a full run was
asked for.

## Steps

1. Make sure the API container is up (`docker ps | grep businessaiagents-api`). The command
   enables the pipeline for its own process only; users are not affected.
2. Run both variants (each writes JSON inside the container):

   ```bash
   docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval \
     --variant naive --output /tmp/research-eval-naive.json [--questions ids]
   docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval \
     --variant optimized --output /tmp/research-eval-optimized.json [--questions ids]
   ```

   Run the optimized variant first only when you want to show cache effects; for a fair
   before/after comparison run naive first so neither variant benefits from the other's cache.
3. Compare:

   ```bash
   docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval-compare \
     /tmp/research-eval-naive.json /tmp/research-eval-optimized.json
   ```

4. Report the table, then call out regressions: citation_coverage below 1.0, completion_rate
   below 1.0, perspective_coverage or entity_recall dropping, or wall time/calls rising.
   Copy the JSON files to `docs/evaluations/research-agent/` only if asked to keep them.

Metric definitions live in `apps/api/app/evaluation/research_agent.py`; the questions in
`apps/api/app/evaluation/research_eval_v1.json`.
