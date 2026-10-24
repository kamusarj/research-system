# Session: Graph polish, provider preflight, Discord gateway, source politeness

Date: 2026-07-26 23:20 +07
Agent: Claude Code (Opus 5)

## User Request

Finish the completion goal (Harness intake #19).

## Work Completed

Goal areas C6-C12, E2, all of D, B10, B13, E3-E5. The goal is now fully implemented.

### Graph rendering, states and accessibility (C6-C12)

- An empty branch explains itself and links to intake, instead of rendering a blank canvas.
  Ten of the eleven pillars were in that state.
- A board card with no children no longer offers "Expand →" onto nothing.
- Source-type, confidence and date filters are hidden in hierarchy view, where canonical
  ontology nodes carry none of those attributes and the controls could only empty the view.
- Search now finds matches anywhere in the tree through `/ontology/search` and jumps to
  them. Filtering the visible branch could never reveal a match three levels down.
- Every graph node is keyboard reachable with an accessible name; selection is announced
  through an `aria-live` region. Previously only hierarchy boards were focusable.
- One colour and label system for both views, with node types translated rather than shown
  as PascalCase identifiers.
- **Defect found and fixed by measurement**: three-viewport Playwright checks found 23 node
  labels escaping the canvas on mobile. `resize()` repositioned the hierarchy but never
  re-fitted it, so a narrow viewport kept the previous scale. All 9 viewport cases now pass
  with no horizontal page scroll, no escaping labels and no console errors.
- Removed the superseded Cytoscape renderer, its layout helpers and the `cytoscape`
  dependency. It was dead since the D3 migration and referenced only by its own test.

### Provider preflight (E2)

- `GET /api/v1/ai/providers?preflight=true` contacts each configured provider's cheapest
  authenticated endpoint, caching each result for 60 seconds so a polling UI cannot
  multiply requests. Neither the credential nor the response is returned or logged.
- The intake page shows per-provider state and explains the cost of an unreachable one.
- **This immediately surfaced a real fact**: on the live runtime the configured OpenAI key
  does not answer, while DeepSeek and Mistral do. That was previously invisible until a
  source had already been fetched, classified and failed.

### Discord intake gateway (D1-D6)

New app at `apps/discord-bot`, opt-in through the `discord` Compose profile.

- Allowlisted guilds and channels, closed by default; the process refuses to start without
  an explicit allowlist rather than accepting intake from any server it is invited to.
- Multiple URLs and PDF attachments per message, bounded at 20 links and 5 files, with
  anything beyond that reported rather than silently cut.
- Idempotent on the Discord message ID, which the API pairs with each normalized URL.
  Attachment bytes are persisted through the API before asynchronous processing starts.
- Bilingual status reactions and per-item replies. An actionable failure is explained; an
  unrecognised code is named rather than guessed at.
- `/submit` and `/status` slash commands.
- Scoped service-account authentication with `intake:submit` and `intake:read-own` only, so
  the bot cannot approve, publish or change the graph.
- Added `GET /api/v1/intake/receipts?occurrence_ref=` so a person holding a Discord message
  ID can ask about it. The lookup is confined to the caller's own namespace.
- All 33 gateway tests run without Discord or a network; the Discord glue stays thin.

### Source politeness and caching (B10, B13)

- Per-host request spacing, so a queue of links from one domain no longer arrives as fast
  as the worker can issue requests.
- `robots.txt` support, off by default so an upgrade does not silently change what an
  existing deployment collects. An unreachable robots file permits the fetch, because an
  outage must not look like a publisher's decision.
- Conditional GET: responses record their `ETag`/`Last-Modified`, and a request carrying
  them raises `NotModified` instead of downloading an unchanged page again.

## Files Changed

New: `apps/discord-bot/**` (gateway, messages, config, rate limit, API client, bot, tests,
Dockerfile, README), `apps/api/app/services/sources/politeness.py`,
`apps/api/tests/test_source_politeness.py`, `apps/api/tests/test_provider_preflight.py`,
`apps/web/components/intake/provider-status.tsx` (+ test),
`apps/web/components/knowledge-graph/graph-legend.test.tsx`,
`apps/web/components/knowledge-graph/graph-filters.test.tsx`,
`apps/web/e2e/viewport-check.spec.ts`.

Removed: `apps/web/components/knowledge-graph/graph-canvas.tsx` (+ test),
`apps/web/lib/knowledge-graph/graph-layouts.ts`, the `cytoscape` dependency.

Changed: `apps/api/app/services/{ai,sources/http}.py`, `apps/api/app/api/{ai,intake_receipts}.py`,
`apps/api/app/core/{config,auth}.py`, `apps/api/app/services/intake_receipts.py`,
`apps/web/app/{graph,ingestion}/page.tsx`, `apps/web/app/globals.css`, `apps/web/lib/i18n.tsx`,
`apps/web/lib/knowledge-graph/{graph-theme,d3-graph-renderer,ontology-api}.ts`,
`apps/web/components/knowledge-graph/{graph-legend,graph-filters,node-details-panel}.tsx`,
`docker-compose.yml`, `Makefile`, `.env.example`.

## Commands and Results

- `make test` — 242 backend, 33 Discord gateway, 66 frontend (341 total)
- `make lint` — clean across all three apps
- `npx tsc --noEmit`, `npm run build` — clean, 15 routes
- `npx playwright test e2e/viewport-check.spec.ts` — 9 passed across three viewports
- `docker compose --profile discord build discord-bot` — image builds; the container
  refuses to start unconfigured and names every missing variable
- API and worker images rebuilt; live stack healthy on `18000`
- `harness-cli story complete` passed for all four completion stories, each running its
  real proof command

## Known Issues

- Conditional GET is implemented at the fetch layer, but no caller persists validators
  between submissions yet, so the saving currently applies only within a single fetch that
  is given them. Persisting them needs a schema column and is not done.
- Per-host rate limiting and the robots cache are per process. The worker is a single
  process today; scaling it out would make these per-replica budgets.
- Relationship-view nodes still reconcile with zero ontology nodes on the live data,
  because the seeded ontology and the current classifications do not overlap yet.
- The Discord bot has not been run against a real Discord application; that needs a token
  and an allowlisted server, which only the owner can provide.

## Next Best Action

Owner decisions: review link change set `42ae7795-280e-4ee1-8525-2462cc061074` and decide
whether to apply it; replace or remove the OpenAI credential the preflight now shows as
not answering; provide a Discord token and allowlist to run the gateway for real.
