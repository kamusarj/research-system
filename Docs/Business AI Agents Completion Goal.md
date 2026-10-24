# Business AI Agents — Completion Goal

Owner: Linh. Authorized 2026-07-26. Harness intake #19 (high-risk, new initiative).

> Ghi chú 2026-09-04: các yêu cầu song ngữ trong mục tiêu lịch sử này đã được quyết định
> 0044/DEC-057 thay thế. Sản phẩm hiện chỉ phát hành giao diện và thông báo bằng tiếng Việt; dữ liệu
> nghiên cứu gốc vẫn giữ nguyên ngôn ngữ.

## Goal Statement

Close every functional gap between "a link is submitted" and "the knowledge graph is
correct and usable", make link extraction fail gracefully and actionably instead of
opaquely, make the graph workspace navigable at any depth, and ship the Discord intake
bot as a thin, authenticated gateway adapter. The project is done when a person can drop
a URL (in the web app or in Discord), and — without reading logs — understand exactly
what happened to it and see it land in the right place in the knowledge graph.

## Baseline (measured 2026-07-26)

| Signal | Value | Source |
| --- | --- | --- |
| Backend tests | 168 passing | `apps/api/.venv/bin/python -m pytest` |
| Frontend tests | 32 passing | `npm test` in `apps/web` |
| Link submissions recorded | 27 | `GET /api/v1/ingestion/links` |
| `ResearchItem` nodes in relationship graph | 3 | `GET /api/v1/graph/stats` |
| Ontology pillars with children | 1 of 11 | `GET /api/v1/graph?view=hierarchy` |
| Failed submissions with opaque `INTERNAL_ERROR` | 1 | intake list |

The test suites are green while the product is not. Every item below is a behavioral
defect or missing capability that the current tests do not cover.

## A. Link intake never reaches the knowledge graph

The central defect. Uploaded documents flow `document -> document_graph ->
ontology_mapping -> change set -> KnowledgeNode`. Link submissions have no equivalent
path: approving one only creates a `ResearchItem`, which appears in the flat
*relationship* projection and never in the *hierarchy* projection the owner treats as
the main graph.

- **A1** Route approved link submissions through the same ontology mapping and change-set
  review path as uploaded documents, so a link proposes placed nodes/edges under the
  eleven pillars instead of a disconnected `ResearchItem`.
- **A2** Surface the review backlog: 24 of 27 completed submissions were never approved,
  so they contribute nothing. Add a visible needs-review count, bulk approve/reject, and
  make the auto-approve confidence threshold discoverable in the UI.
- **A3** Reconcile relationship-view taxonomy nodes (`tag:*`, `technology:*`) against
  canonical ontology `KnowledgeNode` labels and aliases so the same concept is not two
  different nodes in two views.
- **A4** Refresh dependent projections (Neo4j, Meilisearch, pgvector) when a change set is
  applied or a submission is approved; today they silently go stale.
- **A5** Fix duplicate handling: a submission can be marked `duplicate` against an
  unapproved original whose `research_id` is null, so it disappears with no graph
  contribution and no recovery path in the UI.

## B. Link content extraction fails opaquely

- **B1** Replace the `ResearchSystem/1.0` user agent with a realistic browser UA plus
  `Accept-Language`, and add a per-host header override table. The current UA is refused
  by common publishers.
- **B2** Widen accepted content types (`application/xhtml+xml`, `text/markdown`,
  `application/json`, charset-suffixed values) and match by prefix; reject before
  downloading the whole body rather than after.
- **B3** Resolve charset properly (header -> `<meta charset>` -> detection fallback).
  Vietnamese pages currently risk mojibake from `response.encoding` alone.
- **B4** Replace the `len(text) < 80` JavaScript-render heuristic with real content-quality
  detection: boilerplate ratio, consent/paywall/captcha markers, main-content extraction.
- **B5** Make the Browserless render fallback actually reachable — it is gated behind a
  disabled flag and a container that is not started by default — and degrade cleanly when
  the container is down.
- **B6** Replace opaque `INTERNAL_ERROR` / "The source could not be processed" with an
  actionable bilingual error taxonomy: what failed, why, and what the user can do next.
  Preserve diagnostic detail server-side without leaking secrets.
- **B7** Register `TRANSCRIPT_SOURCE_INVALID` in `SourceErrorCode`; it is raised but not
  declared, so the UI cannot map it.
- **B8** Give Facebook Reels an honest path: they always return `PARTIAL` /
  `TRANSCRIPT_UNAVAILABLE`. Explain the limitation in the UI and enrich from public
  metadata where permitted instead of silently degrading.
- **B9** Fix retry semantics: the in-fetch retry counter compounds with worker-level
  retries (up to attempts x attempts), and `time.sleep` blocks the worker thread.
- **B10** Add conditional GET / content caching so resubmitting a URL does not refetch the
  full body.
- **B11** Close the SSRF time-of-check/time-of-use window between the validator's DNS
  resolution and httpx's own, and handle IPv6-only hosts consistently.
- **B12** State the scanned-PDF limitation explicitly when OCR is disabled instead of
  returning a generic extraction failure.
- **B13** Add per-host politeness: rate limiting and `robots.txt` awareness.

## C. Knowledge graph display and navigation

- **C1** Hierarchy drilldown only opens `SystemPillar` nodes one level deep. Children with
  their own children are dead ends. Support recursive drilldown at any depth with a real
  breadcrumb stack.
- **C2** Breadcrumb entries all invoke the same collapse handler; clicking any crumb does
  the same thing regardless of position.
- **C3** Remove silent truncation: the root view caps at 16 nodes and an expanded board at
  40, while one pillar already holds 33 children. Paginate or virtualize instead.
- **C4** `expandNode` is a no-op in hierarchy view but the node inspector still offers an
  Expand action.
- **C5** Header metrics mix global relationship stats with locally visible hierarchy counts,
  so the numbers do not describe what is drawn.
- **C6** Ten of eleven pillars are empty and render as blank boards. Add an empty state that
  explains why and links to intake.
- **C7** Verify and fix node overlap, label truncation, edge routing through nodes, and
  zoom/fit behavior at desktop, tablet, and mobile viewports.
- **C8** Relationship view caps at 40 degree-sorted nodes with no pagination and no way to
  focus a specific research item from search.
- **C9** Search filters the hierarchy but does not reveal the path to matches; add
  search-to-focus that expands ancestors.
- **C10** Hide source-type, date, and confidence filters in hierarchy view where they have
  no effect.
- **C11** Make graph nodes keyboard reachable and announce selection changes.
- **C12** Unify the legend and colour system across the two views, which currently share one
  component but use disjoint node-type vocabularies.

## D. Discord intake bot

Constraints carried forward from DEC-028: the bot stays a thin gateway adapter. All
extraction and research logic remains in the API and worker.

- **D1** Allowlisted guild/channel gateway authenticating to the API with a scoped service
  account, posting to `/api/v1/intake/receipts`.
- **D2** Multiple URLs per message plus PDF attachments, with attachment bytes persisted
  before asynchronous processing begins.
- **D3** Idempotency on `discord_message_id + normalized_url` without losing repeated-source
  provenance.
- **D4** Status reactions and replies covering queued, extracted, partial, failed, and
  duplicate, with bilingual actionable text.
- **D5** Slash commands for status, search, graph lookup, and retry.
- **D6** Deployment: Compose service, file-mounted secrets, health endpoint, rate limiting,
  and no business logic in the bot process.

## E. Cross-cutting quality

- **E1** The worker logs `Intake worker loop failed` with no cause. Log the exception and
  apply bounded backoff.
- **E2** Provider reachability is `null` for OpenAI, DeepSeek, and Mistral and false for
  Ollama; surface a preflight status in the UI so a misconfigured provider is visible
  before a submission fails.
- **E3** Add regression coverage for every path above, including an end-to-end case that
  submits a link, approves it, and asserts it appears in the hierarchy graph.
- **E4** Bilingual EN/VI strings for every new user-facing message.
- **E5** Keep `Docs/`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and a session log current.

## Definition of Done

1. A URL submitted through the web app or Discord produces a reviewable, correctly placed
   proposal in the hierarchy graph, and applying it makes the node visible under a pillar.
2. Every extraction failure produces a specific bilingual reason and a next action; no
   `INTERNAL_ERROR` without detail remains reachable through normal use.
3. The graph workspace navigates to any depth, truncates nothing silently, and renders
   correctly at desktop, tablet, and mobile.
4. The Discord bot runs as a deployed Compose service under a scoped service account and
   is idempotent on replay.
5. Backend, frontend, and end-to-end suites pass, with new cases covering each fix above.

## Discord Gap-Alert Extension (authorized 2026-07-30)

Harness intake #23 and story `US-DISCORD-GAP-ALERTS` extend D1-D6 without widening the
gateway's authority:

- Discord URL receipt items request guarded auto-approval by default. The existing
  complete-source and confidence guards remain authoritative.
- Approved links refresh persisted low-coverage knowledge gaps after they create the
  approved research/relationship-graph contribution and governed hierarchy change set.
- Scoped receipt reads expose only active gaps related to the receipt item's research
  tags; the bot renders them in its bilingual channel reply.
- The bot retains only `intake:submit` and `intake:read-own`. Partial Reels, low-confidence
  sources and canonical hierarchy mutations keep their existing human-review gates.
