---
name: research-report
description: Run a cited deep-research report on a business AI agents question through the team's research system (planner → web/knowledge-base search → quote verification → writer) and save the Markdown report. Use when someone asks to research, investigate or write a sourced brief/report about AI agents for business (market, use cases, vendors/competitors, technical architecture, risk/compliance), or types /research-report <question>.
---

# Research report

Runs the research system's own pipeline instead of answering from memory, so every sentence in
the result cites a source whose exact quote was found in that source. The report is saved as a
draft that a human reviews in the web app before it is published.

## Steps

1. Take the question from the arguments (Vietnamese or English, 10–1000 characters). If none
   was given, ask for it in one sentence.
2. Run, from the repository root:

   ```bash
   scripts/research-report.sh "<question>"
   ```

   - Local runtime: no configuration needed (`http://localhost:13000/api/v1`).
   - Team deployment: set `RESEARCH_API_URL=https://<team-domain>/api/v1` and
     `RESEARCH_API_TOKEN` to a service-account token with scopes `research:run` and
     `research:read` (an owner creates it at `POST /api/v1/auth/service-accounts`). Never print
     or commit the token.
   - A run takes about 3–6 minutes; the script prints each stage and waits up to 20 minutes.
3. When it finishes, read the saved file under `research-reports/` and reply with:
   - the 3–5 most decision-relevant findings, each keeping its `[n](url)` citation exactly as
     written in the report;
   - the "Khoảng trống bằng chứng" section (perspectives with no verified evidence), if any;
   - the path of the saved file and the web link to review the draft.
4. Do not add facts, numbers or sources that are not in the report. If the user wants more
   depth on a perspective, run a new, narrower question rather than filling gaps yourself.

## When it fails

| Message | Meaning and next step |
|---|---|
| `FEATURE_DISABLED` | The owner must set `RESEARCH_AGENT_ENABLED=true` and start SearXNG (`docker compose --profile research-agent up -d searxng`). |
| `RESEARCH_RUN_ACTIVE` | The account already has a run in progress; wait for it or cancel it in the web app. |
| `RESEARCH_DAILY_BUDGET_EXCEEDED` / HTTP 429 | Daily or per-minute limit reached; try later. |
| `NO_SOURCES`, `NO_READABLE_SOURCES` | Search returned nothing usable; rephrase with more specific terms. |
| `NO_VERIFIED_CLAIMS` | Sources were found but no claim could be verified against its quote; narrow the question. |
