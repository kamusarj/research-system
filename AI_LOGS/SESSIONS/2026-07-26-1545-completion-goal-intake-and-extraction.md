# Session: Completion goal, intake-to-graph path and extraction resilience

Date: 2026-07-26 15:45 +07
Agent: Claude Code (Opus 5)

## User Request

Linh asked to set a goal for finishing the project and to run a fixing loop through the
Harness: check the link-intake to knowledge-graph path, fix failures when a link's content
cannot be collected, fix the graph display thoroughly, build a Discord bot for deployment,
and brainstorm the remaining defects into the goal so the loop can clear them all.

## Baseline Measured Before Any Change

- 168 backend tests and 32 frontend tests passing.
- 27 link submissions recorded; only 3 `ResearchItem` nodes in the relationship graph.
- 10 of 11 ontology pillars empty; no link submission had ever reached the hierarchy.
- One submission failed with an opaque `INTERNAL_ERROR` and empty details.
- Worker logged `Intake worker loop failed` with no cause, because the JSON formatter
  deliberately drops `exc_info`.

## Decisions Made

- The goal is recorded in `Docs/Business AI Agents Completion Goal.md` as five work areas
  (A intake-to-graph, B extraction resilience, C graph display, D Discord bot, E quality),
  each item traced to measured evidence rather than speculation.
- Exception *messages* stay out of logs and out of persisted rows, per the existing
  production-safe observability decision. Diagnosability comes from exception type and
  code location instead, which are repository-owned and cannot carry secrets.
- Link submissions reach the canonical hierarchy through the same governed change-set
  path that uploaded documents use. Nothing is written to the canonical graph without a
  human approving the proposal.
- HTTP-level retries now cover transport faults only. Responses the server chose to send
  (429, 5xx) are surfaced as retryable so the worker reschedules them with backoff,
  instead of both layers multiplying attempts against a struggling site.
- A browser-render failure no longer replaces the source's own limitation. "This page
  needs JavaScript" is actionable for a researcher; "the renderer is down" is not.

## Files Changed

- `Docs/Business AI Agents Completion Goal.md` (new)
- `apps/api/app/core/observability.py` — `exception_fields`, `exception_location` field
- `apps/api/app/core/config.py` — worker backoff, UA, Accept-Language, per-host headers
- `apps/api/app/worker.py` — cause-carrying error log and bounded backoff
- `apps/api/app/services/ingestion.py` — error taxonomy, browser-recoverable limitations,
  change-set creation on approval
- `apps/api/app/services/sources/errors.py` — expanded taxonomy, actionable/retryable sets
- `apps/api/app/services/sources/http.py` — browser identity, content-type aliases checked
  before download, charset resolution, bot-challenge detection, peer-address SSRF check
- `apps/api/app/services/sources/quality.py` (new) — consent/paywall/JS detection
- `apps/api/app/services/sources/article.py` — uses the quality assessment
- `apps/api/app/services/ocr.py` — `PDF_SCANNED_OCR_DISABLED`
- `apps/api/app/services/link_mapping.py` (new) — link submission to ontology proposals
- `apps/web/lib/i18n.tsx` — 31 bilingual error titles and remediation hints
- `apps/web/components/intake/submission-error.tsx` (new)
- `apps/web/components/intake/submission-list.tsx` — translated errors and limitations
- `apps/web/app/globals.css` — submission error styles
- Tests: `test_source_quality.py` (new), `test_link_to_hierarchy.py` (new), additions to
  `test_observability.py`, `test_ingestion.py`, `test_sources.py`

## Commands and Results

- `apps/api/.venv/bin/python -m pytest` — 202 passed (from 168)
- `apps/api/.venv/bin/python -m ruff check .` — clean
- `npm test` in `apps/web` — 35 passed (from 32)
- `npx tsc --noEmit` and `npm run lint` — clean
- Live runtime on API `18000`: submitted `https://arxiv.org/abs/2210.03629`, extraction and
  DeepSeek classification completed, approval produced link change set
  `42ae7795-280e-4ee1-8525-2462cc061074` with 16 mutations, 16 valid, 0 errors, 1 warning.

## Verification Result

The central defect is closed and proven on the real runtime: a submitted URL now becomes a
reviewable set of canonical placements under the eleven pillars. Extraction failures now
carry a specific code and a bilingual next action instead of "The source could not be
processed".

## Known Issues

- Applying the live change set has not been done; that is the product owner's decision.
- Graph display work (recursive drilldown, truncation, metrics, accessibility) is not
  started.
- The Discord bot is not started.
- Relationship-view taxonomy nodes are still not reconciled against canonical ontology
  labels, so a concept can appear twice across the two views.

## Next Best Action

Continue the goal loop at task 5: intake review backlog, duplicate handling against
unapproved originals, and projection refresh on apply.
