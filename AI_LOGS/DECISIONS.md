# Decisions

## DEC-001 - Local-first MVP

- Date: 2026-07-09
- Status: accepted
- Decision: bắt đầu bằng MVP chạy local thay vì full platform production.
- Reason: workspace hiện mới có docs, hệ thống brainstorm rất rộng; local-first giúp có bản dùng được nhanh và giảm rủi ro overbuild.
- Consequences:
  - Phase đầu tập trung Research KB.
  - Production hardening, SSO, Kubernetes, full collector và fine-tune pipeline để sau.

## DEC-002 - Research KB là ưu tiên đầu tiên

- Date: 2026-07-09
- Status: accepted
- Decision: ưu tiên lưu trữ research, CRUD, search, graph và AI enrichment cơ bản trước.
- Reason: đây là lõi của hệ thống và là nền tảng cho auto-collector/training data.
- Consequences:
  - Collector chỉ làm MVP một source sau core.
  - Training Data Hub chỉ làm foundation sau MVP.

## DEC-003 - Markdown AI Handoff Log trước database

- Date: 2026-07-09
- Status: accepted
- Decision: dùng thư mục `AI_LOGS/` với Markdown files để handoff giữa AI agents.
- Reason: chưa có backend/database, Markdown trong repo dễ đọc, ít phụ thuộc, dùng được ngay khi đổi agent hoặc hết quota.
- Consequences:
  - Mỗi agent phải đọc `AI_LOGS/HANDOFF.md` và `AI_LOGS/TASKS.md` trước khi làm.
  - Mỗi phiên đáng kể phải cập nhật handoff/session log.
  - Sau này có thể đưa vào Research System qua API riêng.

## DEC-004 - Không lưu secret/PII trong AI logs

- Date: 2026-07-09
- Status: accepted
- Decision: AI logs không được chứa secrets, tokens, credentials, customer PII hoặc nội dung nhạy cảm.
- Reason: logs nằm trong repo và được nhiều agent đọc.
- Consequences:
  - Nếu cần ghi lỗi liên quan secret, chỉ mô tả loại lỗi và file/config liên quan, không paste giá trị secret.

## DEC-005 - Repo-level agent instruction files

- Date: 2026-07-09
- Status: accepted
- Decision: tạo instruction files ở root repo để nhiều AI agents tự nhận quy trình handoff mà không cần prompt riêng.
- Files:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `OPENCODE.md`
  - `ANTIGRAVITY.md`
  - `.github/copilot-instructions.md`
- Reason: các tool khác nhau đọc các convention khác nhau; dùng `AGENTS.md` làm chuẩn chung và bridge files cho tool phổ biến giúp giảm rủi ro agent bỏ qua `AI_LOGS`.
- Consequences:
  - Agent mới phải đọc `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, và `AI_LOGS/DECISIONS.md`.
  - Không đảm bảo 100% mọi tool tự động đọc các file này; nếu tool không hỗ trợ, user vẫn cần trỏ một lần vào `AGENTS.md`.

## DEC-006 - Lightweight projections for the local MVP

- Date: 2026-07-11
- Status: accepted
- Decision: implement search and graph from the primary database first, while preserving `/api/v1` contracts and rebuild semantics.
- Reason: this is the explicit lightweight path in the implementation plan and keeps the first local release operable with three containers.
- Consequences:
  - PostgreSQL remains canonical in Docker and SQLite supports isolated tests.
  - Meilisearch, pgvector-native vectors and Neo4j can replace projections without changing frontend routes.
  - Mock AI is deterministic by default; Ollama is selected through configuration.

## DEC-007 - Governed training export

- Date: 2026-07-11
- Status: accepted
- Decision: block training-example acceptance unless PII, policy and provenance checks pass.
- Reason: the implementation plan explicitly requires governance before fine-tuning data can be used.
- Consequences:
  - Only accepted examples enter built dataset versions.
  - Export is JSONL; no model training runner is included in MVP.

## DEC-008 - Deployable-app monorepo layout

- Date: 2026-07-12
- Status: accepted
- Decision: place deployable services under `apps/`, using `apps/api` for FastAPI and `apps/web` for Next.js; keep repository-wide runtime entrypoints and required agent/docs directories at root.
- Reason: the previous sibling `backend/` and `frontend/` layout mixed application code with repository-level concerns and did not provide a clear extension rule for future workers or services.
- Consequences:
  - Compose build contexts, bind mounts, Make targets, and development documentation use the new paths.
  - Future deployables belong under `apps/`.
  - Add `packages/` only for proven reusable code, not as an empty abstraction.

## DEC-009 - Persisted gaps with human-approved deep research

- Date: 2026-07-13
- Status: accepted
- Decision: Gap Intelligence v1 detects concepts attached to at most one approved research item, persists the gap lifecycle in PostgreSQL, and creates deep-research reports as drafts that require the normal human review transition before approval.
- Reason: this is the smallest rebuildable Phase 8 slice that uses the stable graph/KB foundation without introducing an autonomous agent or background infrastructure.
- Consequences:
  - `POST /api/v1/gaps/detect` is the explicit mutating detection action; `GET /api/v1/gaps` and `GET /api/v1/graph/gaps` are read-only.
  - Dismissed gaps remain dismissed on subsequent scans.
  - Approved reports mark their linked gap filled; failed-search/trend signals and weekly digest remain follow-up work.

## DEC-010 - Source-neutral intake and structured multi-provider AI

- Date: 2026-07-13
- Status: accepted
- Decision: Discord is deferred to an adapter over a source-neutral URL intake API. All providers implement structured JSON output validated into the same domain schema; PostgreSQL owns submission/workflow state and graph remains a rebuildable typed projection.
- Reason: extraction, classification, policy and graph behavior must be testable without Discord and must not depend on one model vendor.
- Consequences:
  - Intake records source type/reference, content hash, provider/model provenance, retryable status and linked research ID.
  - OpenAI uses Responses structured output; DeepSeek/OpenRouter use their documented Chat Completions-compatible formats; Gemini and Ollama use their native transports.
  - Provider API keys are environment-only and provider status never returns secret values.
  - Discord work begins only after completion Gates A-C; its idempotency key will derive from message ID and normalized URL.

## DEC-011 - PostgreSQL-backed intake worker foundation

- Date: 2026-07-13
- Status: accepted
- Decision: make URL intake asynchronous with `link_submissions` as the durable local-first job queue. A separate worker claims rows using a lease, retries transient failures with exponential backoff, and moves permanent or exhausted failures to `dead-letter` for explicit manual retry.
- Reason: this removes slow fetch/model work from API requests and provides crash/retry safety without making Redis a source of truth or blocking the local MVP on new infrastructure.
- Consequences:
  - New link submissions return HTTP 202 in `queued` state; duplicate URL submissions still return HTTP 200.
  - PostgreSQL `FOR UPDATE SKIP LOCKED` supports multiple worker processes; expired `extracting` leases are reclaimable.
  - Redis may be added later as queue transport, while PostgreSQL retains durable job state.
  - The intake UI polls only while jobs are active and exposes bilingual queued/processing/retry/dead-letter states.

## DEC-012 - Normalized source adapters and bounded graph contract

- Date: 2026-07-13
- Status: accepted
- Decision: route URL intake through a normalized GitHub/article/Facebook Reel/PDF adapter contract and expose graph data only through a validated, bounded `{nodes, edges, meta}` response. PostgreSQL remains the default provider; mock and Neo4j implementations share the provider boundary.
- Reason: source-specific collection must evolve without duplicating workflow schemas, and graph visualization must never render the full database or depend on UI-hardcoded data.
- Consequences:
  - GitHub and Article perform practical extraction first; Facebook Reel and PDF use explicit pending states until transcript/text-layer processing exists.
  - `approved` remains the current published/searchable/graph-visible research state.
  - Graph queries enforce node/edge/depth/neighbor limits and reject duplicate, dangling, self-loop or malformed responses.
  - Neo4j selection fails explicitly until its idempotent projection adapter is implemented; it never silently falls back or returns fake data.

## DEC-013 - Staged URL pipeline with independent review state

- Date: 2026-07-15
- Status: accepted
- Decision: run every supported URL through an observable, source-neutral pipeline with typed adapters and keep machine processing state separate from human review state.
- Reason: a single overloaded status field hid failures, made retries ambiguous, and prevented the UI from reporting where a job stopped.
- Consequences:
  - Processing uses `pending`, `processing`, `fetching`, `extracting`, `analyzing`, `completed`, `partial_success`, and `failed`; review uses `not_requested`, `needs_review`, `approved`, `rejected`, or `duplicate`.
  - GitHub repository/file/issue/pull request, public Facebook metadata, scientific-paper metadata, direct PDF, and generic article adapters all emit one normalized document contract.
  - Fetching revalidates public destinations at every redirect, streams bounded responses, and applies separate request-level and durable-job retry limits.
  - Incomplete but useful extraction is persisted as `partial_success` with a machine-readable limitation; access controls, paywalls, private Facebook content, scanned-PDF OCR, and JS-only rendering are never bypassed or silently reported as complete.

## DEC-014 - Smart Exam visual language for the Research workspace

- Date: 2026-07-15
- Status: accepted
- Decision: rebuild the Research System frontend using `/home/linh/smart-exam-ai` as the visual reference while preserving the Research domain, routes and bilingual workflows.
- Reason: the product owner requested visual consistency with the existing Smart Exam application rather than a separate neutral/sidebar design.
- Consequences:
  - The application uses a sticky topbar, spark brand, pill navigation/actions, ivory canvas, warm red-orange primary color, white/bone surfaces, soft shadows and the same typography scale.
  - Inter is bundled locally through `@fontsource/inter`; the local-first UI does not depend on Google Fonts at runtime.
  - Tablet and mobile retain all routes through a scrollable navigation row rather than hiding navigation at the reference app's desktop breakpoint.
  - Base Compose always uses relative `/api/v1` requests through `API_PROXY_TARGET`; it does not forward a stale host `NEXT_PUBLIC_API_URL` into the local browser bundle.

## DEC-015 - Deep-ocean product identity and bounded host Ollama bridge

- Date: 2026-07-15
- Status: accepted; supersedes only the color-palette portion of DEC-014.
- Decision: keep the proven sticky topbar, pill navigation, responsive route access and Inter typography, but give Research System a distinct navy/teal/indigo palette. Add an opt-in `local-ai` Compose profile that bridges only Ollama tags, version and generate routes from a loopback-only host Ollama service into Docker.
- Reason: the product owner requested a different visual tone and real testing with an already-installed local model without downloading model artifacts or exposing the host Ollama API to the LAN.
- Consequences:
  - Core canvas/action tokens are `#f3f7f8` and `#0b6f76`; graph colors and the application icon follow the same palette.
  - Primary text/action contrast is verified at WCAG AA ratios across the new palette.
  - The bridge defaults to Docker's internal `172.17.0.1:11435`, rejects arbitrary routes including `/api/pull`, and never downloads a model.
  - Ollama structured requests disable thinking, send the actual JSON Schema in `format`, and use temperature zero before Pydantic validation.
  - Provider status distinguishes a configured Ollama endpoint from a reachable installed model; cloud providers are not probed merely to render the intake form.

## DEC-016 - No application AI mock fallback

- Date: 2026-07-17
- Status: accepted; supersedes the AI-mock portions of DEC-006 and the earlier MVP provider defaults. It does not change the isolated graph contract test provider in DEC-012.
- Decision: remove the in-process AI mock provider from the application registry, request schema, UI and runtime defaults. Use configured Mistral as the current default, retain Ollama and other real providers as selectable adapters, and keep deterministic AI behavior only inside automated tests.
- Reason: the product owner explicitly requested removal of mock behavior. A missing provider must be visible as unavailable instead of producing synthetic results that look like model output.
- Consequences:
  - `GET /api/v1/ai/providers` exposes only Ollama, OpenAI, DeepSeek, Gemini, OpenRouter and Mistral.
  - Intake requests with `provider=mock` fail validation with HTTP 422.
  - The frontend selects an active configured/reachable provider and disables submission if none is available.
  - Existing completed rows retain their historical provider provenance; no past data is rewritten or deleted.
  - Backend tests inject a deterministic provider double at the test boundary and never register it in application runtime.

## DEC-017 - Registry-neutral DOI fallback and PostgreSQL-safe search

- Date: 2026-07-17
- Status: accepted.
- Decision: keep Crossref as the first DOI metadata lookup, then use bounded DOI CSL content negotiation when Crossref reports a missing record. Implement tag search/filter with relationship `EXISTS` predicates instead of joining tags and applying SQL `DISTINCT` to full research rows.
- Reason: valid DataCite-managed DOIs are not guaranteed to exist in Crossref, and PostgreSQL cannot apply `DISTINCT` equality to the current JSON columns even though the same query passes on SQLite.
- Consequences:
  - DOI redirects remain public-address validated, bounded by the existing fetch limits, and parsed into the same normalized paper contract.
  - A DOI and its arXiv URL can safely converge through content-hash deduplication without a false `SOURCE_NOT_FOUND`.
  - Search works consistently on SQLite tests and the PostgreSQL runtime without duplicate result rows or JSON equality errors.
  - Live PostgreSQL search after intake approval is a required runtime smoke check, not inferred from SQLite tests.

## DEC-018 - Graph Intelligence v2 implementation defaults

- Date: 2026-07-18
- Status: accepted.
- Decision: begin phased implementation of `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md` using the eleven-pillar ontology, paper-fit threshold 60, PDF/Markdown/text uploads up to a configurable 20 MB default, draft-only `evidence_pending` ideas, one preferred display parent plus optional semantic parents, and explicit approval for every change set.
- Chat decision: build a ChatGPT-like product UI backed by a server-side OpenAI Responses API adapter with `store: false` by default. Keep graph-chat orchestration provider-neutral and never expose a publish/delete tool or API key to the browser.
- Reason: the product owner explicitly authorized implementation and confirmed that chatbot behavior may call OpenAI directly.
- Consequences:
  - Phase 0-1 may proceed without waiting for the previously open product questions.
  - OpenAI is the first graph-chat tool-calling adapter, not a replacement for the existing multi-provider registry.
  - Unsourced chat ideas cannot enter the published graph until reviewed and supported according to policy.
  - Defaults remain configurable and may be superseded by a later accepted decision.

## DEC-019 - Local-state governed graph chat

- Date: 2026-07-18
- Status: accepted.
- Decision: persist graph-chat state locally and send each OpenAI Responses request with `store: false`; rebuild bounded, redacted context from local history instead of relying on provider conversation state. Expose strict read/propose tools only, and route every proposed mutation through the existing graph change-set review workflow.
- Reason: brainstorming needs useful graph context and tool use without giving a model direct publication authority or making the cloud provider the source of truth for business conversation state.
- Consequences:
  - The server stores chat sessions, messages, provider/request provenance, tool activity and linked change sets; API keys never enter the browser or chat logs.
  - Function schemas use strict object validation, bounded tool loops and configured message/context/proposal limits.
  - No chat tool can publish, delete, execute SQL, access the filesystem or perform arbitrary network calls.
  - Unsourced proposals remain `evidence_pending`; only validated, human-approved change sets can update the canonical graph.
  - OpenAI is the first adapter behind the provider-neutral interface. Other providers may be added without changing chat persistence or graph governance.

## DEC-020 - Reversible local rollout controls and deterministic release gates

- Date: 2026-07-18
- Status: accepted.
- Decision: gate Graph Intelligence v2, document workspaces and chat independently at the server; protect costly local mutations with configurable sliding-window limits; require deterministic gold evaluation, graph invariants, migration parity and backup/restore evidence before product acceptance.
- Reason: Phase 6 needs a reversible rollout and repeatable evidence without silently changing the accepted rubric or depending on a live provider for every regression run.
- Consequences:
  - Disabled v2 routes return typed `FEATURE_DISABLED` errors while legacy Research CRUD and the relationship graph remain available.
  - The local limiter is process-local and keyed by client address; production replicas require authenticated identity and a gateway/shared limiter.
  - Every API response includes process timing headers; slow requests are logged without bodies or secrets.
  - Gold metrics describe the versioned fixture only. Real provider quality, schema failures, cost and latency remain production observability metrics.
  - Product-owner acceptance cannot be inferred from automated tests and remains an explicit checklist decision.

## DEC-021 - Routed local and MinIO attachment storage

- Date: 2026-07-21
- Status: accepted.
- Decision: keep attachment object references opaque and route them by scheme. Existing plain keys
  permanently mean local storage; new remote writes use `minio://<configured-bucket>/<object-name>`.
  Reads and deletes support both forms, backend selection changes only new writes, and no object is
  migrated or deleted automatically.
- Reason: Gate C requires MinIO attachments, but reinterpreting existing local keys through a global
  backend switch would make persisted content unavailable and make rollback unsafe.
- Consequences:
  - Local filesystem remains the default and the current named volume remains authoritative for
    historical plain keys until a separately authorized migration is completed.
  - Production MinIO provisioning, TLS/encryption, lifecycle, backup and credentials remain external
    deployment responsibilities; secrets never enter APIs or AI logs.
  - A deployment with MinIO-key rows must keep valid MinIO read configuration even if new writes are
    rolled back to local.
  - The public document API and database schema remain unchanged.

## DEC-022 - Production-safe operational observability

- Date: 2026-07-21
- Status: accepted.
- Decision: use correlated JSON stdout logs with a strict field allowlist and bounded-label
  Prometheus metrics. Keep `/metrics` disabled by default and require an independently
  configured bearer secret when enabled. Use route templates and typed outcomes rather than
  raw paths or business identifiers. PostgreSQL `AuditEvent` remains the authoritative
  product audit trail.
- Reason: Gate C needs actionable runtime evidence without leaking research documents, chat
  content, provider credentials, or arbitrary headers into logs or metric labels.
- Consequences:
  - API metrics are process-local and reset on restart; the worker emits structured job logs
    but opens no unauthenticated scrape listener.
  - External deployment owns scraper secret injection, TLS/network policy, retention,
    dashboards, and any multi-process aggregation.
  - Operational telemetry never replaces durable audit records.

## DEC-023 - Local authentication, RBAC and file-mounted secrets

- Date: 2026-07-21
- Status: accepted.
- Decision: add opt-in local authentication with Argon2 password hashes, random opaque server-side
  sessions hashed at rest, HttpOnly/SameSite cookies and CSRF validation. Enforce the server-side
  hierarchy `owner > researcher > viewer`, keep canonical publication/review/apply and user
  administration owner-only, and bind authenticated actor IDs into audit/review provenance.
- Deployment decision: local trusted mode remains reversible, while staging/production configuration
  fails closed unless auth and Secure `__Host-` cookies are enabled. Runtime settings may read
  service-scoped files from `/run/secrets`; direct secret environment variables remain for local
  backward compatibility only.
- Consequences:
  - PostgreSQL becomes part of login/session availability and supports explicit session revocation.
  - Operators provision the first owner through password stdin and terminate HTTPS externally.
  - OIDC/Keycloak, MFA, tenant isolation and Discord service accounts remain separate follow-ups.

## DEC-024 - Bounded optional source enrichment

- Date: 2026-07-21
- Status: accepted.
- Decision: keep direct public HTTP and PDF text-layer extraction primary. Add disabled-by-default,
  fail-closed Browserless rendering only for JS-partial articles and PDFium/Tesseract OCR only for
  scanned PDFs. Validate every browser subrequest, block heavy resources and bound all browser/OCR
  time, bytes, pages, pixels and output. Allow validated user-supplied timestamped transcripts only
  for unpublished public Facebook Reel/video submissions, then reprocess all derived fields and
  retain owner publication review.
- Reason: Gate C needs useful extraction without expanding into unrestricted browser automation,
  unbounded native processing, Facebook login/media download or automatic social transcription.
- Consequences:
  - Provider absence/failure preserves useful partial metadata with typed limitations.
  - Transcript bodies stay out of queue responses and audit logs; audit retains safe actor/language/count metadata.
  - Browserless is internal-only and digest-pinned; production still owns egress policy and capacity.
  - Automatic Reel download/transcription requires a separate platform-policy and credential decision.

## DEC-025 - Idempotent Neo4j relationship and hierarchy projection

- Date: 2026-07-21
- Status: accepted.
- Decision: keep PostgreSQL as the only canonical store and project the validated `relationship`
  and `hierarchy` graph views into optional Neo4j rows identified by `(projection, graph_id)`.
  Explicit owner-only rebuilds use composite constraints, parameterized batched `UNWIND`/`MERGE`
  and one managed transaction for both view upserts plus stale-row pruning. Selected-provider reads
  include bounded graph query, hierarchy branch, shortest path and cluster behavior with no silent
  PostgreSQL fallback.
- Reason: Gate C explicitly requires Neo4j to be demonstrated as a rebuildable projection, while
  retries, partial replacement and a second canonical write path must remain impossible.
- Consequences:
  - Graph payloads are schema-validated before write and after read; service/config/payload failures
    return typed secret-free errors.
  - Projection freshness remains an explicit operation until a separately justified durable outbox
    exists; full snapshot transactions need capacity testing for much larger corpora.
  - The optional Compose service is internal-only and digest-pinned. Production TLS, clustering,
    backup, resource sizing and secret rotation remain deployment responsibilities.

## DEC-026 - Atomic search and semantic vector projections

- Date: 2026-07-21
- Status: accepted.
- Decision: keep PostgreSQL research rows canonical. Build approved-only Meilisearch data in a
  complete validated staging index and atomically swap it into the live name. Store bounded document
  chunks separately as real Mistral `mistral-embed` output in pgvector `vector(1024)` rows with an
  HNSW cosine index. Lexical and semantic providers are independently selected; selected external
  providers fail visibly and return ranked IDs that the API hydrates from current approved
  PostgreSQL rows.
- Reason: Gate C requires rebuildable Meilisearch/pgvector evidence, while the legacy SHA-derived
  JSON arrays do not demonstrate semantic retrieval and external search data must never become a
  second source of truth.
- Consequences:
  - Meilisearch swap and PostgreSQL vector replacement are each atomic, but deliberately do not
    pretend to form a distributed transaction; a repeat rebuild converges both projections.
  - Rebuild is an explicit owner operation until a separately justified durable outbox consumer
    exists. The PostgreSQL/lexical defaults remain available for lightweight local use.
  - Meilisearch is internal-only and digest-pinned; Mistral availability/cost is required only for
    pgvector rebuild/query when selected. Production key scoping, TLS/network policy, backup and
    capacity remain deployment responsibilities.

## DEC-027 - Copy-verify legacy object migration

- Date: 2026-07-21
- Status: accepted.
- Decision: provide an operator-only, dry-run-first migration command. Explicitly confirmed
  execution copies each valid plain-key local object to the configured MinIO object name, reads the
  remote copy back, verifies byte count and SHA-256 plus the retained local source, then commits the
  matched attachment/workspace references and a bounded audit event. Each object commits
  independently so repeat runs converge. No command mode deletes a local object or volume.
- Reason: changing the write backend does not move historical bytes, while updating references
  without remote read-back proof or removing the source would create silent data-loss risk.
- Consequences:
  - A complete clean plan is required before any copy; missing/mismatched rows stop execution.
  - A crash before reference commit may leave an orphan remote object, which a rerun safely
    overwrites and re-verifies from the retained local source.
  - Production MinIO readiness, backups, execution and later local-volume retirement remain explicit
    operator decisions outside application automation.

## DEC-028 - Source-neutral intake receipts and items

- Date: 2026-07-21
- Status: accepted and implemented locally.
- Decision: separate external source occurrences from processing aggregates. `IntakeReceipt`
  represents one manual/API/platform occurrence and `IntakeReceiptItem` represents each normalized
  URL or durably stored document. Existing `LinkSubmission` and `DocumentGraphWorkspace` remain the
  jobs. Same occurrence/item replays converge, while a different occurrence of the same URL creates
  independent provenance linked to the existing job.
- Reason: unique-URL intake correctly prevents duplicate processing but currently discards later
  source provenance and cannot model one message containing multiple URLs/PDFs safely.
- Consequences:
  - Migration `a8b4c6d2e913` is additive, backfills every legacy submission without reprocessing,
    keeps legacy provenance columns through rollback proof, and uses database uniqueness as the
    final concurrency guard.
  - Documents must be validated, durably stored and hash-verified before asynchronous acknowledgement;
    audit/logs exclude message bodies, user profiles, tokens, raw URLs and filenames.
  - External adapters require revocable namespace-scoped service authentication. Discord remains a
    thin adapter and cannot start until Graph v2, deployment Gate C and all receipt entry criteria pass.

## DEC-029 - Provider-neutral graph-chat acceptance with temporary DeepSeek default

- Date: 2026-07-21
- Status: accepted; supersedes the OpenAI-only acceptance dependency in DEC-018/DEC-019 while
  preserving their OpenAI adapter, local-state and governance requirements.
- Decision: support both DeepSeek Chat Completions tool calling and OpenAI Responses behind the
  existing graph-chat provider protocol. Use DeepSeek as the current configurable default and allow
  a later environment-only switch back to OpenAI.
- Reason: the product owner explicitly authorized the configured DeepSeek provider so project
  completion is not indefinitely blocked by a rejected OpenAI credential.
- Consequences:
  - DeepSeek uses non-thinking mode and adapter-specific message/tool-result translation.
  - All cloud context remains bounded/redacted and all tool arguments still pass application-side
    Pydantic validation.
  - Both providers expose only read/propose tools; proposals remain draft-only until human
    validation, approval and apply.
  - Final acceptance requires a real configured provider walkthrough, not specifically OpenAI.

## DEC-030 - Discord guarded auto-ingest and scoped knowledge-gap alerts

- Date: 2026-07-30
- Status: accepted and implemented locally.
- Decision: Discord URL receipt items request the existing guarded auto-approval path by default.
  The API still requires complete extraction and the configured confidence threshold. Link approval
  refreshes the persisted low-coverage detector, and namespace-scoped receipt reads include at most
  ten active gaps whose concept keys match the approved research item's tags. The gateway renders a
  deduplicated bounded set in the normal bilingual channel reply.
- Reason: the gateway already submitted and polled source-neutral receipts, but it did not request
  auto-approval or expose the knowledge gaps caused by an approved graph contribution. The bot must
  remain a replaceable adapter rather than gaining research, gap or graph mutation authority.
- Consequences:
  - The service account remains limited to `intake:submit` and `intake:read-own`; there is no direct
    gap endpoint or owner credential in the bot.
  - Complete high-confidence links enter the approved relationship graph automatically and create
    governed hierarchy change-set proposals. Canonical hierarchy apply remains human-reviewed.
  - Partial Reels without supplied transcripts and low-confidence sources remain reviewable and do
    not auto-publish.
  - Real Discord delivery still requires an owner-provided token and guild/channel allowlist.

## DEC-031 - Automatic Discord intake and current pin authorization

- Date: 2026-07-30
- Status: accepted and implemented locally.
- Decision: ordinary allowlisted messages containing supported links/PDFs are the primary
  zero-command intake path; `/submit` is optional compatibility. `/pin message_id:<id>`
  operates only in the interaction's current allowlisted channel and requires Discord's
  resolved `PIN_MESSAGES` permission for both caller and bot. IDs are unsigned 64-bit
  snowflakes, already-pinned targets are idempotent, and successful mutations carry a
  bounded Discord audit reason.
- Reason: the owner clarified that link intake must never require a command and requested
  command-triggered channel pinning. Pinning is a Discord state mutation, so intake
  allowlisting alone is not sufficient authorization. Discord requires the separate
  `PIN_MESSAGES` permission after 2026-02-23.
- Consequences:
  - The gateway depends on `discord.py>=2.7.1,<3` for the current permission flag.
  - `/pin` never searches another channel, adds no Research API/service-account scope and
    returns bounded ephemeral outcomes.
  - Installers and permitted callers must receive Pin Messages explicitly; Administrator
    is not requested.
  - Live Discord mutation still requires owner credentials. Repository proof invokes the
    actual callback with credential-free platform doubles.

## DEC-032 - Remove the Training Data Hub and its persisted domain

- Date: 2026-07-30
- Status: accepted and implemented locally; supersedes the Training Data Hub direction in the
  MVP specification and implementation plan.
- Decision: remove the Training Data browser route, API, authorization rules, ORM models, seed
  behavior, feature tests and current product commitments. Migration `e1f7a9c3b205` drops the
  six related tables and all existing rows. Its downgrade recreates empty schema only.
- Reason: the owner explicitly requested removal of everything related to Training Data. Hiding
  navigation alone would leave reachable contracts and retained data.
- Consequences:
  - One example, one dataset and one dataset-membership row were permanently deleted.
  - `/training` and `/api/v1/training/*` are no longer product contracts.
  - Historical migrations, decisions, AI logs and original brainstorm sources remain immutable
    audit history; they do not reactivate the retired feature.
  - Reintroducing dataset-building requires a new decision, schema and story.

## DEC-033 - Per-user local cache for unsaved document authoring

- Date: 2026-07-30
- Status: accepted and implemented locally.
- Decision: cache one versioned, bounded direct-authoring draft per authenticated user and browser
  origin in localStorage. Draft title, editable source format, content and update time remain local
  until explicit creation. Successful governed upload or explicit discard clears the cache; an
  error retains it.
- Reason: the owner requires direct document entry and F5-safe work, while unsaved business text
  must not leak across users, enter logs or silently become canonical server data.
- Consequences:
  - Markdown, TXT, LaTeX, reStructuredText, AsciiDoc and HTML creation reuse the existing multipart
    upload, object storage, provenance, AI-processing and review contracts.
  - The browser cache is limited to two million characters and never contains uploaded PDF/DOCX
    bytes.
  - LocalStorage is not encrypted or cross-device; users sharing a browser profile should explicitly
    discard their draft before handoff.
  - Collaborative/server-side autosave remains a separate data-model and concurrency decision.

## DEC-034 - Not adopting LightRAG; keep the existing custom RAG

- Date: 2026-07-31
- Status: accepted.
- Decision: do not integrate LightRAG (or any external RAG framework). Keep the in-house RAG
  already implemented and proven on the runtime: Mistral `mistral-embed` chunks in pgvector
  `vector(1024)` + HNSW cosine (DEC-026), approved-only atomic Meilisearch projection, document
  canonical-text extraction feeding document-scoped and graph-scoped chat (intake #29 /
  `US-DOCUMENT-SCOPED-CHAT-CONTEXT`, DEC-019/DEC-029), and the governed knowledge graph
  (PostgreSQL source of truth + optional Neo4j projection per DEC-025 + D3 visualization at
  `/graph`).
- Reason: an owner request asked whether any RAG was applied, whether LightRAG should be added so
  the AI can read documents, and whether LightRAG can display a knowledge graph. Inspection showed
  the repo already has a complete custom RAG and that `lightrag` appears nowhere in the code; the
  owner then chose not to add LightRAG. LightRAG's own embedding/vector/key-value/graph storage,
  entity-relation extraction and graph retrieval would duplicate DEC-026 (pgvector) and DEC-025
  (Neo4j) and bypass the governed change-set workflow (DEC-019), conflicting with the locked
  architecture direction in `AGENTS.md` (FastAPI, Next.js, PostgreSQL+pgvector, Neo4j, Meilisearch,
  Redis, MinIO, Ollama). The "AI reads documents" need is already met by document-scoped chat plus
  pgvector semantic search.
- Findings recorded:
  - Retrieval: `apps/api/app/services/search_projection.py`, `apps/api/app/models.py:259`,
    migration `c5a8e2f4b901`; lexical via Meilisearch, semantic via pgvector.
  - Augmented generation: `apps/api/app/api/chat.py`, `apps/api/app/services/graph_chat.py`
    (bounded redaction + context limit + `store=false`).
  - Knowledge graph display already exists at `/graph` (D3 hierarchy + relationship views, 45
    nodes / 32 edges); LightRAG has no first-party graph UI and would still need the existing
    Neo4j/Cytoscape/D3 render path.
- Consequences:
  - No LightRAG dependency, Compose service, intake, schema or migration is added.
  - Any future revisit requires a new decision; if pursued, LightRAG must run only as an optional
    experimental projection that never writes the canonical graph or replaces pgvector/Neo4j,
    and must preserve provenance/governance.
  - No code, schema or runtime change was made; this entry is the only artifact of the request.

## DEC-035 - Import public ChatGPT shares as one-way local snapshot forks

- Date: 2026-08-01
- Status: accepted and implemented locally.
- Decision: accept only official public `https://chatgpt.com/share/<id>` URLs and retrieve one
  bounded, cookie-free snapshot. Persist visible user/assistant text plus immutable source
  provenance in the local chat domain, label imported message origin, and keep every later turn
  local. Never treat a share ID as an OpenAI conversation ID or write/synchronize back to ChatGPT.
- Reason: ChatGPT shared links are public snapshots, not a supported Responses/Conversations API
  continuation contract. A local fork preserves useful context without introducing user cookies,
  private-account access or remote mutation authority.
- Consequences:
  - Exact-host, public-network peer, redirect, HTML byte, message-count and character bounds are
    enforced before persistence; oversized imports fail visibly instead of truncating silently.
  - System instructions, reasoning, tool internals and model context are excluded. Images and files
    are not downloaded and appear only as omission placeholders.
  - Imported text passes through the existing history/context bounds and cloud redaction before a
    configured DeepSeek/OpenAI provider receives a local continuation.
  - Audit records contain source type, snapshot hash and aggregate counts only—no URL, title, HTML
    or transcript.
  - Upstream share-page format changes return typed parse errors; supporting a new format requires
    bounded parser/test updates, not weaker access controls.

## DEC-036 - Render imported chat Markdown and cache anonymous shared images locally

- Date: 2026-08-02
- Status: accepted and implemented locally; amends DEC-035's original asset exclusion.
- Decision: render visible chat text with sanitized GitHub-flavored Markdown and raw HTML disabled.
  Treat direct allowlisted OpenAI HTTPS images and current generated-image `sediment://file_*`
  records as display-only media. Resolve sediment records only through ChatGPT's anonymous shared
  asset endpoint using the same share ID and anonymous-session cookies, validate public peers,
  bounded redirects, raster MIME types and image byte limits, retry transient asset failures twice,
  then persist immutable bytes through the existing object-storage boundary. Expose only a bounded
  same-origin media URL to the browser and never add media URL/key metadata to AI provider history.
- Reason: the first implementation displayed Markdown syntax literally and dropped current ChatGPT
  generated images because those images are emitted as tool-role sediment pointers, not direct
  HTTPS message parts. Anonymous public-share resolution preserves fidelity without account access.
- Consequences:
  - Raw tool text, private attachments, authenticated assets, SVG/HTML media and non-allowlisted
    URLs remain excluded.
  - Import failure after object writes removes those objects; unavailable images remain explicit
    placeholders while text import can continue.
  - Previously imported sessions cannot recover discarded pointers and must be imported again.
  - Image availability after a successful import no longer depends on an expiring signed URL.

## DEC-037 - Human-reviewed inline document AI and automatic scoped RAG

- Date: 2026-08-02
- Status: accepted and implemented locally.
- Decision: make uploaded Markdown/TXT source editable through immutable object-backed versions.
  An AI rewrite is bound to the exact source version, selected range and selected-text hash, and
  remains a draft proposal until an owner or researcher explicitly accepts it. Manual save, Accept
  and restore each create a new version and requeue extraction/evaluation/graph processing.
- Decision: refresh that document's existing pgvector chunks automatically after successful
  extraction. Draft chunks are authorized only inside their document scope and are explicitly
  excluded from global approved search; RAG failure is visible and independently retryable.
- Reason: users need ChatGPT-style selected-text assistance without giving the model overwrite or
  publication authority, and uploaded documents should become retrievable without a manual global
  projection rebuild.
- Consequences:
  - Editor cache is bounded and keyed by authenticated user, workspace and source version; F5 can
    restore unsaved text but browser storage is not canonical or cross-device.
  - Old derived graph/evidence is cleared before a changed source is evaluated, preventing stale
    facts from surviving a low-score or failed graph rebuild.
  - Audit/log payloads contain IDs, hashes, counts and provider/model metadata, not document text,
    selections, replacements or raw provider responses.
  - DOCX/PDF rich editing, collaborative merge and historical-object retention remain follow-ups.

## DEC-038 - Contextual selection actions and focused chat layout

- Date: 2026-08-02
- Status: accepted and implemented locally.
- Decision: show a viewport-clamped floating action popover next to selected text in both the
  Markdown/TXT document editor and Brainstorm chat. Document buttons continue to create a proposal
  that requires Accept. Chat buttons prepare a bounded Markdown quote plus Ask AI, Explain or
  Summarize instruction in the local composer and require explicit Send; selection never transmits
  content or changes message history.
- Decision: replace Brainstorm chat's three-column desktop layout with session history plus one
  flexible conversation column. Move scope/provider/status into compact thread chips, keep graph
  review links in their originating messages, and remove duplicated Graph context, Knowledge
  changes summary and Tool activity cards.
- Reason: browser-only selection gave no application actions in chat, the document toolbar was easy
  to miss in long source, and the right rail narrowed the main work area and caused avoidable
  overflow on common Windows laptop viewports.
- Consequences:
  - Closed chat selection can prepare a prompt and opens the existing new-chat form; it still cannot
    send until the user creates an active session and presses Send.
  - The desktop topbar switches to accessible labeled icons at 1440px and below rather than clipping
    later routes; title attributes and aria-labels preserve discoverability.
  - Tool-call diagnostics remain in message/API data but no longer consume normal product UI space.
  - No backend route, provider behavior, database, audit or retention contract changed.

## DEC-039 - Unified editable source import and stateless document brainstorm

- Date: 2026-08-02
- Status: accepted and implemented locally.
- Decision: treat Markdown, TXT, LaTeX, reStructuredText, AsciiDoc and HTML as editable UTF-8
  source throughout Document workspace. Importing one of these formats populates the existing
  per-user local authoring draft before creation, and uploaded source remains editable through the
  immutable version workflow. Keep PDF and DOCX as binary/read-only references until a byte-faithful
  rich-document editing design exists.
- Decision: add contextual AI chat beside the pre-create and uploaded-source editors through a
  stateless endpoint. The endpoint sends only bounded, cloud-redacted current source, optional
  selected range and bounded recent local history to the configured DeepSeek/OpenAI graph-chat
  provider with no tools. It stores no chat, document or version rows. AI output changes only the
  browser draft after explicit Replace selection, Insert at cursor or Append; Create/Save remains a
  separate governed action.
- Reason: users need to import, write, edit and brainstorm in one document surface without an early
  upload round trip, while the model must not silently overwrite source or create hidden durable
  conversations. Attempting rich PDF/DOCX editing through plain text would lose layout and fidelity.
- Consequences:
  - Provider responses render as sanitized Markdown, but source syntax remains raw and editable.
  - Pre-create brainstorm history is local component state and is intentionally not restored by F5;
    the document draft itself remains F5-safe under DEC-033.
  - Prompt/source/selection/response bodies do not enter logs or audit records; provider/model and
    bounded context metadata may be returned to the user.
  - Wide screens use an editor/chat split; widths at and below 1440px stack the panels to preserve
    usable Windows, tablet and mobile layouts.

## DEC-040 - Conflict-safe instant AI patches for local document drafts

- Date: 2026-08-02
- Status: accepted and implemented locally; amends DEC-037's proposal-first interaction for the
  current browser draft without changing its durable version boundary.
- Decision: a structured AI edit is bound to the exact full-source revision, selected range and
  original text. Low/medium-risk prose may replace that range immediately in the local cached draft
  and must expose Undo and View diff. A late response fails closed if the source or selection no
  longer matches.
- Decision: numbers, citations, URLs, code/formulas, semantic-change requests and cloud-redacted
  selections are high risk and remain review-only with explicit Apply/Discard. The provider route is
  bounded, redacted, tool-free, rate-limited and stateless; it never writes document content,
  versions, proposals, RAG rows or graph state.
- Reason: the owner asked for ChatGPT-style editing directly in the document rather than a separate
  proposal/Accept round trip, while factual and structural content still needs a human-controlled
  safety boundary.
- Consequences:
  - Create document and Save new version remain the only durable source mutations and continue to
    trigger the existing automatic document-scoped RAG lifecycle.
  - Undo is range-safe and local to the most recent applied patch; it fails instead of overwriting
    intervening edits.
  - Expand can auto-apply when it preserves ordinary prose, but warns that it may add claims; custom
    semantic-change instructions require review.
  - PDF/DOCX rich editing, collaborative merge and cross-device draft synchronization remain out of
    scope.

## DEC-041 - Align document AI proxy budgets and simplify authoring hierarchy

- Date: 2026-08-03
- Status: accepted and implemented locally.
- Decision: keep the Next.js same-origin rewrite proxy alive for 125 seconds, slightly longer than
  the API's 120-second provider deadline. Preserve typed provider failures, normalize malformed
  provider containers to `AI_RESPONSE_INVALID`, and show localized editor errors. Only transient
  failures expose a user-triggered Retry; the client never automatically duplicates a provider call.
- Decision: keep title, format, editable import, editor, contextual AI, cache state and explicit
  Create/Save as the primary workflow. Collapse safe Raw/Preview/Side-by-side inspection and binary
  PDF/DOCX upload until requested; remove repeated descriptions and the separate upload-policy card.
- Reason: live evidence showed the API finishing a valid DeepSeek edit after 33.8 seconds while the
  default 30-second proxy had already returned a generic 500. The page also repeated the same source
  and policy explanation at equal visual priority with the editor.
- Consequences:
  - Valid slow edits are not converted into proxy failures before the API deadline.
  - Retry remains explicit, cost-aware and protected by the same source-revision checks.
  - Required source preview modes and binary upload remain available without dominating the page.
  - No database, source-version, RAG, graph, auth, authorization or audit boundary changes.

## DEC-042 - Review every changed document AI patch before local application

- Date: 2026-08-04
- Status: accepted and implemented locally; supersedes DEC-040's automatic low/medium-risk apply
  path without changing its stateless or durable persistence boundaries.
- Decision: every changed instant-edit response remains a browser-only pending patch until the user
  sees the complete original/replacement comparison and explicitly chooses Accept or Reject. Risk
  and warnings remain review context but never bypass review. Identical replacement text alone maps
  to the no-change message.
- Decision: treat the user's action/custom instruction as a required transformation over the full
  selected range. Repeat it after bounded context and enforce deterministic output contracts when
  the requested format is verifiable; a whole-source LaTeX conversion must return a standalone
  LaTeX document, while a noncompliant provider response is typed as `AI_RESPONSE_INVALID`.
- Reason: the owner requires VS Code-style before-mutation review and reported that a requested
  whole-text LaTeX conversion was being ignored. Live DeepSeek evidence reproduced the unchanged
  output, then proved the corrected contract with a valid review-only LaTeX patch.
- Consequences:
  - Simple grammar/prose edits require one additional Accept click.
  - Reject never changes source; Accept rechecks the original revision/range before local mutation.
  - `auto_apply_allowed` stays in the compatible API response but is always false.
  - Create/Save remains the only durable source mutation and RAG trigger.
  - Provider calls remain bounded, redacted, tool-free, rate-limited and persistence-free.

## DEC-043 - Bounded XeLaTeX PDF preview

- Date: 2026-08-04
- Status: accepted and implemented locally.
- Decision: replace the heuristic-only LaTeX Preview with an ephemeral XeLaTeX compile endpoint
  that returns a PDF for browser embedding. Compile with shell escape disabled in a fresh temporary
  directory under source, PDF, wall-time, CPU, memory, file-size, descriptor and process limits.
- Reason: mapping template macros cannot reproduce the actual layout, fonts, TikZ or package
  behavior users see in Overleaf.
- Consequences:
  - The API image includes TeX Live and Noto fonts and is substantially larger.
  - Compile requests require researcher access, CSRF in auth mode and a local rate-limit budget.
  - Source, raw logs and PDF are not persisted; typed errors fall back to the safe text preview.
  - Shell escape, request-time package downloads, multi-file projects and external assets remain
    unsupported. A dedicated sandbox service is required before untrusted multi-tenant rollout.

## DEC-044 - Explicit recovery for Document Brainstorm provider failures

- Date: 2026-08-04
- Status: accepted and implemented locally; extends DEC-041's cost-aware explicit retry policy to
  contextual Document Brainstorm.
- Decision: map typed provider/transport failures to localized safe feedback, retain the exact
  failed question and its pre-request history in ephemeral browser state, and expose Retry only for
  retryable failures. Retry remains user-triggered and must not add a duplicate user bubble.
- Reason: live DeepSeek telemetry showed a real brainstorm call reaching the 120-second deadline;
  the UI exposed raw provider text and gave no recovery action.
- Consequences:
  - Provider timeout can still occur, but the question is not lost and can be retried explicitly.
  - No automatic paid retry, silent provider fallback or longer deadline is introduced.
  - Stateless/redacted provider transmission and explicit local Apply/Create/Save boundaries remain
    unchanged.

## DEC-045 - Route contextual chat edit commands to reviewed patches

- Date: 2026-08-04
- Status: accepted and implemented locally; amends DEC-039's advisory-only contextual chat behavior
  for direct edit imperatives and preserves DEC-042 review-before-apply.
- Decision: deterministically route Vietnamese/English mutation commands from contextual document
  chat to the existing custom instant-edit pipeline. Use the native selection when present, or the
  complete source only within the existing 20,000-character bound. Questions remain advisory chat.
- Reason: the owner requires `sửa tên thành ...` to create a source patch with complete
  Original/Proposed and Accept/Reject, not an explanatory brainstorm response.
- Consequences:
  - One Send calls either brainstorm or instant edit, never both.
  - Accept alone changes the local draft; Reject preserves it; Create/Save remains durable.
  - Oversized whole-source edits ask for an explicit bounded selection.

## DEC-046 - Preserve standalone LaTeX structure across whole-source AI edits

- Date: 2026-08-04
- Status: accepted and implemented locally; strengthens DEC-042 and DEC-045.
- Decision: when an instant-edit selection is the complete current source and that source is already
  a standalone LaTeX document, accept provider output only if it is another standalone LaTeX
  document with `\documentclass`, `\begin{document}` and a terminal `\end{document}`. Markdown
  fences, non-comment prefaces, missing boundaries, duplicate terminal boundaries and trailing
  commentary are invalid. Enforce this invariant in the API and again in the browser before Accept.
- Reason: the owner showed a rename response whose explanatory Markdown was accepted as the entire
  Raw source, breaking compilation instead of changing the name in place.
- Consequences:
  - Invalid provider output gets typed safe feedback and cannot become Proposed or Raw content.
  - Valid complete LaTeX edits retain full Original/Proposed review; Accept remains the only local
    mutation and Create/Save remains the only durable mutation.
  - Partial LaTeX fragments are not required to be standalone documents.
  - Structural validation does not replace human semantic review.

## DEC-047 - Give the Document AI proxy wall-clock margin

- Date: 2026-08-04
- Status: accepted and implemented locally; supersedes DEC-041's 125-second proxy value without
  changing its explicit Retry or review-before-apply rules.
- Decision: use a bounded 180,000 ms default for the Next.js same-origin API proxy, expose
  `API_PROXY_TIMEOUT_MS` through Compose and fall invalid/non-positive values back to the same
  default. Do not disable the proxy timeout or add automatic retries.
- Reason: live telemetry showed a DeepSeek edit completing successfully with API HTTP 200 in
  131.115 seconds while the 125-second proxy had already reset the browser socket. HTTPX's
  configured 120-second timeout bounds inactivity, not total request wall time.
- Consequences:
  - The observed long success has about 49 seconds of proxy margin.
  - A hung upstream remains bounded; extremely long edits can still fail at 180 seconds and should
    become asynchronous if they are common.
  - No provider, API, schema, persistence, source-version, RAG, graph or review contract changes.

## DEC-048 - Reversibly redact cloud document edits

- Date: 2026-08-04
- Status: accepted and implemented locally; strengthens DEC-042 and DEC-046.
- Decision: document instant edits replace each sensitive value with a unique ephemeral cloud token,
  keep mappings only in request memory, require every selected-source token exactly once in output,
  restore originals before format validation and reject generic/invented/altered/missing/duplicated
  markers. Advisory graph chat retains generic irreversible redaction because it does not replace
  source. XeLaTeX failures expose only a bounded document line number and reason.
- Reason: a provider copied generic email/phone placeholders into a whole-source patch. Accept lost
  the local values and the placeholder underscores broke LaTeX compilation.
- Consequences:
  - Original sensitive values remain absent from provider input and byte-faithful in local review.
  - Redaction artifacts cannot enter Proposed or Raw source.
  - Values already overwritten before this decision require recovery from a trusted original copy.

## DEC-049 - Document Brainstorm concurrency and LaTeX apply guard

- Date: 2026-08-07
- Status: accepted and implemented locally; strengthens DEC-039, DEC-045 and DEC-046 at the browser
  boundary.
- Decision: normalize selection against the current source before edit/apply; make instant-edit `run`
  return success; map chat edit routing to `ready | selection_required | failed | busy`; disable
  brainstorm send while busy and Apply while a reviewed patch is pending; emit local-only chat status
  excluded from provider history; refuse advisory Apply that would break a standalone LaTeX document.
- Reason: owner-requested hidden-bug hunt found concurrent apply/stale-selection/silent chat-edit and
  LaTeX-destroying Append paths despite a green existing suite.
- Consequences:
  - Manual edit and AI chat edit remain available together with Accept/Reject still required.
  - Advisory Append/Replace cannot silently corrupt complete LaTeX sources.
  - No API, schema, persistence, RAG or graph contract changes.

## DEC-050 - Route document selection actions into the brainstorm chat panel

- Date: 2026-08-07
- Status: accepted and implemented locally; UI-only. Intake #55, story
  `US-DOCUMENT-SELECTION-CHAT-ROUTING`.
- Decision: selection popover options (`improve`/`shorten`/`expand`/`fix_grammar`) post a user message
  into the adjacent brainstorm chat and run the same reviewed instant-edit pipeline; the reviewed card
  (diff + Accept/Reject, Undo, Retry) renders inside the chat thread. "Ask AI" and the pane-title edit
  button focus the chat composer. `DocumentInstantEditFeedback` and the `document-custom-ai` input no
  longer render below the editor. Full decision: `docs/decisions/0037-selection-actions-into-chat-panel.md`.
- Reason: owner wants the ChatGPT-Canvas-like flow where selection actions surface in the chat tab next
  to the editor instead of a new chat area below it.
- Consequences:
  - All AI edit review happens in one place (the chat panel), preserving Accept/Reject review.
  - Predefined actions send the localized label as `instruction`; the backend still maps non-custom
    actions via `ACTION_INSTRUCTIONS`, so no behavior change.
  - No API, schema, persistence, RAG or graph contract changes.

## DEC-051 - Two-pane focus edit window with persistent chat history

- Date: 2026-08-07
- Status: accepted and implemented locally; UI-only. Intake #56, story
  `US-DOCUMENT-FOCUS-EDIT-WINDOW`.
- Decision: the Document workspace initially shows only the document content. Selecting text shows the
  action popover; clicking an option opens `DocumentFocusWindow` — a full-screen two-pane portal dialog
  (left: editable text, right: chatbot) with an ✕ button and Escape to close. Edits inside the window
  persist to the underlying document when it closes. The chatbot pane has a "Chat history" toggle
  listing past Q&A sessions persisted per document in localStorage (`document-brainstorm-history:<key>`),
  with "New chat" and session reload. Full decision:
  `docs/decisions/0038-focus-edit-window-and-chat-history.md`.
- Reason: owner wants the ChatGPT-Canvas-like flow — document first, then on-demand two-tab edit window,
  with persistent per-document chat history visible from the chatbot pane.
- Consequences:
  - The always-visible brainstorm panel is replaced by the on-demand window; review/Accept/Reject still
    happen in the chat (DEC-039/045/046/049 preserved).
  - Chat history is local-only and never sent to the provider.
  - No API, schema, persistence, RAG or graph contract changes.

## DEC-052 - Preserve binary originals and edit extracted-text derivatives

- Date: 2026-08-09
- Status: accepted and implemented locally; completes intake #57 / high-risk story
  `US-DOCUMENT-UPLOADED-EDITING` and supersedes only the PDF/DOCX read-only deferral in DEC-039.
- Decision: keep every uploaded PDF/DOCX original immutable as version 1 and expose it separately for
  inline PDF viewing or original download. Make successfully extracted canonical text editable as an
  explicitly labelled UTF-8 derivative under the existing optimistic version, AI review, restore,
  worker processing and RAG contracts. Never overwrite or label derivative bytes as PDF/DOCX.
- Reason: the owner requires uploaded documents to be viewable and editable without accepting the
  data-loss/type-confusion risk of plain-text overwrite or the much larger scope of a layout-faithful
  Office/PDF editor.
- Consequences:
  - Researchers can correct every readable upload from Document workspace.
  - Original attachment references and historical bytes remain unchanged for binary documents.
  - Restoring binary version 1 re-extracts it into a new text derivative.
  - Page/Office layout editing and same-format export remain an optional future product decision.
  - Full decision: `docs/decisions/0039-loss-safe-binary-document-editing.md`.

## DEC-053 - Isolate document analysis and separate the system map

- Date: 2026-08-09
- Status: accepted and implemented locally; completes intake #61 / high-risk story
  `US-DOCUMENT-KNOWLEDGE-GRAPH-WORKSPACE` and supersedes only DEC-018's score-60 document-graph gate.
- Decision: every readable supported upload receives an isolated document graph regardless of
  paper-fit score. Node reads expose a source-grounded summary capped at 200 characters plus optional
  independent AI research and a typed `consistent | different | insufficient` comparison. AI may
  prepare a draft document-origin graph change set but cannot approve, apply, publish or delete.
- Decision: relationship and hierarchy are two projections of the same approved research node
  corpus. Hierarchy derives a deterministic display parent from approved membership relationships.
  The Business AI Agents `SystemRoot`/`SystemPillar` ontology is served separately at
  `/api/v1/graph/system` and `/graph/system`. The browser uses an explicit 1,000-node/4,000-edge
  operational bound instead of the old 100-item display cap.
- Reason: isolated analysis is useful even for low-fit documents; switching graph layout must not
  switch datasets; system architecture remains useful but is a different concern from research
  knowledge.
- Consequences:
  - Paper-fit controls promotion routing and review priority, not isolated graph availability.
  - AI research persists provider/model provenance on derived nodes and never bypasses human graph
    governance.
  - Applied approved relationships update both relationship and hierarchy projections.
  - Full decision: `docs/decisions/0040-document-knowledge-graph-and-system-map.md`.

## DEC-054 - Autosave authoring drafts without a manual discard action

- Date: 2026-08-11
- Status: accepted and implemented locally; supersedes only DEC-033's explicit-discard clearing path.
- Decision: keep the existing synchronous, bounded, per-user `localStorage` write on every Document
  Workspace title/format/content change and preserve refresh/browser-restart recovery. Remove the
  manual `Discard local draft` UI and handler. A successful governed Create remains the only normal
  product event that clears the completed pre-create cache; errors retain it.
- Reason: the owner explicitly requested removal of the whole-draft deletion path so an in-progress
  document is protected from accidental loss during browser crashes, mistaken closure or mistaken
  UI action. The existing local write path already provides network-independent recovery.
- Consequences:
  - Existing cached drafts remain compatible because the storage key/value schema is unchanged.
  - No API, database, auth, AI, RAG, graph or publication boundary changes.
  - Abandoned drafts remain local until overwritten, browser site data is cleared, or creation
    succeeds; browser storage remains unencrypted and does not sync across devices.
  - Full decision: `docs/decisions/0041-document-draft-autosave-only.md`.

## DEC-055 - Summarize Uploaded documents and guard owner-only deletion

- Date: 2026-08-11
- Status: accepted and implemented locally.
- Decision: reduce Uploaded documents to Document, Summary, Size and Actions; derive a bounded,
  whitespace-normalized summary from the research summary or extracted document content; relabel the
  existing workspace route as Edit; and expose confirmed deletion only to owners. Reject deletion
  while processing is active or when an intake receipt/applied document graph change retains
  provenance. A permitted delete removes the upload-created research/workspace dependents, draft
  graph proposals, document chat, projections and stored versions while retaining a content-free
  audit event.
- Reason: the owner requested a smaller useful document library with edit/delete controls, but an
  unconditional cascade could destroy work in flight or reviewed canonical knowledge.
- Consequences:
  - Summary is inexpensive and deterministic; before extraction it shows a clear pending fallback.
  - Researchers can edit but only owners can delete.
  - Applied graph knowledge and receipt lineage require an explicit future retention/rollback flow.
  - Full decision: `docs/decisions/0042-document-library-summary-and-safe-delete.md`.

## DEC-056 - Keep frontend security patches on Next.js 15 Maintenance LTS

- Date: 2026-08-24
- Status: accepted and implemented locally; Harness decision 0043.
- Decision: keep the frontend on Next.js major 15, resolve Next.js and `eslint-config-next` to
  15.5.23, and bound the vulnerable transitive tree with patched `sharp`, `postcss` and `nanoid`
  overrides. Require both full and production npm audits plus static, unit, production-build,
  responsive-browser and rebuilt-runtime proof. Use `npm ci` from the lockfile in the image and
  resynchronize the persistent dependency volume when its complete production/development tree is
  stale.
- Reason: the current audit found high-severity issues, but the patched 15.5 Maintenance LTS line
  removes them without the unrelated risk of a Next.js 16 migration.
- Consequences:
  - Full and production npm audits report zero vulnerabilities on the locked graph.
  - The image and autostart runtime no longer silently retain stale dependency versions.
  - Recheck after the separately announced 2026-08-26 Next.js security release; an unavailable
    future patch cannot be claimed by this decision.
  - Full decision: `docs/decisions/0043-next15-maintenance-security-patch.md`.

## DEC-057 - Dùng tiếng Việt làm ngôn ngữ duy nhất của sản phẩm

- Ngày: 2026-09-04
- Trạng thái: đã chấp nhận và triển khai cục bộ; Harness decision 0044.
- Quyết định: mọi bề mặt do sản phẩm phát hành dùng tiếng Việt tự nhiên, rõ nghĩa và phù hợp với
  người làm nghiên cứu; gỡ bộ chuyển EN/VI và cố định tài liệu HTML ở `vi`.
- Quyết định: giữ nguyên định danh kỹ thuật, mã lỗi, đường dẫn API, khóa JSON, tên công nghệ/mô hình
  và nội dung nghiên cứu gốc để bảo toàn hợp đồng máy và nguồn gốc dữ liệu. Log lịch sử, migration
  và dữ liệu nguồn không bị dịch hồi tố.
- Lý do: giao diện song ngữ trước đây trộn nhiều thuật ngữ tiếng Anh, làm trải nghiệm thiếu nhất
  quán và khó theo dõi hơn đối với người dùng nghiên cứu bằng tiếng Việt.
- Hệ quả:
  - Web, thông báo an toàn của API, cổng Discord và tài liệu hướng dẫn cốt lõi dùng cùng một hệ
    thuật ngữ tiếng Việt.
  - Không còn lựa chọn giao diện tiếng Anh; nội dung bên ngoài vẫn được giữ nguyên ngôn ngữ gốc.
  - Quyết định đầy đủ: `docs/decisions/0044-vietnamese-only-product-language.md`.

## DEC-058 - Giao diện là không gian làm việc nghiên cứu

- Ngày: 2026-09-04
- Trạng thái: đã chấp nhận và triển khai cục bộ; Harness decision 0045.
- Quyết định: tổ chức frontend theo mô hình “research workspace”: sidebar chia nhóm trên desktop,
  thanh ngữ cảnh cho vùng nội dung và điều hướng ngang đầy đủ trên tablet/mobile. Giữ nhận diện xanh
  đại dương nhưng dùng nền giấy dịu, bề mặt phẳng, đường viền rõ, ít pill/bóng đổ và phân cấp chữ
  mạnh hơn.
- Quyết định: triển khai thiết kế chủ yếu qua app shell và token/component CSS dùng chung; giữ nguyên
  hợp đồng API, URL, phân quyền, dữ liệu và hành vi nghiệp vụ. Mọi nội dung giao diện tiếp tục chỉ
  dùng tiếng Việt theo DEC-057.
- Lý do: giao diện cũ vẫn giống dashboard chung và thanh điều hướng desktop quá dày, chưa tối ưu cho
  việc đọc, duyệt và kết nối tri thức lâu dài.
- Hệ quả:
  - Các trang hiện có nhận diện thống nhất mà không cần viết lại logic nghiệp vụ.
  - Mọi thay đổi layout lớn sau này phải kiểm tra sidebar desktop và navigation tablet/mobile.
  - Quyết định đầy đủ: `docs/decisions/0045-research-workspace-ui-redesign.md`.

## DEC-059 - API cá nhân tạm thời cho trò chuyện

- Ngày: 2026-09-05; đã triển khai cục bộ; Harness intake #8 / decision 0046.
- Cho phép researcher/owner dùng API key OpenAI/DeepSeek của chính họ cho create/import/send
  trong `/chat`. Giữ khóa trong bộ nhớ trang và request server; không lưu browser storage,
  database hay log; đổi tài khoản/rời trang/tải lại phải nhập lại.
- Chỉ lưu nguồn khóa `system|personal` cùng provider/model. Phiên personal thiếu khóa không
  dùng khóa hệ thống; mỗi request khởi tạo provider instance riêng trên endpoint cố định.
- Mở rộng DEC-010/018/019: khóa do người dùng nhập có mặt tạm trong browser; khóa máy chủ
  tiếp tục không được trả về browser. Chat vẫn thuộc kho chung của nhóm theo quyền hiện hành.
- Không thêm lưu khóa lâu dài, endpoint tùy ý hoặc thay đổi nhà cung cấp cho worker/tài liệu.
- Quyết định đầy đủ: `docs/decisions/0046-ephemeral-personal-chat-api.md`.

## DEC-060 - Chọn và kiểm tra mô hình API cá nhân trước khi kết nối

- Ngày: 2026-09-05; đã triển khai cục bộ; Harness intake #9 / decision 0047.
- Theo phản hồi người dùng, thay text model bằng danh sách tải trực tiếp qua key;
  chỉ lưu kết nối vào bộ nhớ trang sau kiểm tra model thật qua adapter chat thành công.
- Kiểm tra chỉ khi bấm nút đã ghi khả năng có phí: tối đa 16 token đầu ra, timeout
  20 giây, prompt tổng hợp, không dữ liệu nghiên cứu/tool execution/retry/fallback.
- Model list không xác nhận credit. Phân biệt xác thực, quyền/model, credit, spend/
  usage/quota, rate limit và mạng bằng mã an toàn; không echo upstream message/key.
- Giữ DEC-059 về khóa tạm và lịch sử shared. Kết quả cũ không dùng khi đổi khóa/model;
  khóa nhập lại cho phiên cũ phải kiểm tra đúng mô hình cố định của phiên.
- Quyết định đầy đủ: `docs/decisions/0047-personal-chat-model-validation.md`.

## DEC-061 - Lớp phủ triển khai nhóm và cổng xuất bản chỉ dành cho chủ sở hữu

- Ngày: 2026-10-14; Harness intake #10 / story `US-TEAM-DEPLOYMENT-READINESS` / decision 0048.
- Triển khai nhóm bằng `docker-compose.team.yml` phủ lên `docker-compose.yml` (không file production
  độc lập): ảnh đóng gói mã, `DEPLOYMENT_ENVIRONMENT=production`, `AUTH_MODE=local`, cookie
  `__Host-` Secure, API/DB không mở cổng, lối vào HTTPS bằng Caddy (`https`) hoặc Cloudflare Tunnel
  (`tunnel`). Cùng tên dự án `businessaiagents` để dùng lại dữ liệu cục bộ. Vận hành qua
  `scripts/team.sh`/`make team-*`; autostart chạy chế độ nhóm khi có `.env.team`.
- API và worker dùng chung anchor `x-app-environment` để không lệch cấu hình.
- Mọi đường xuất bản/duyệt (bulk-review, quyết định mutation, cấu hình nguồn RSS) chỉ owner; tự
  duyệt chỉ hiệu lực với owner hoặc tài khoản dịch vụ; researcher không sửa nghiên cứu
  `in-review`/`approved`; change set chỉ sửa/duyệt ở `draft`/`needs_review`.
- Giới hạn tần suất theo tài khoản; đăng nhập sai giới hạn theo tài khoản và IP thật
  (`FORWARDED_ALLOW_IPS=*` chỉ trong chế độ nhóm vì API không mở cổng).
- Thêm `POST /auth/me/password`, trang `/members` (owner) và `/account`.
- Quyết định đầy đủ: `docs/decisions/0048-team-deployment-and-review-gates.md`.

## DEC-062 - Dùng quota CLI đăng ký (Claude Code/Codex/Antigravity) thay API AI

- Ngày: 2026-10-23; Harness intake #11 / story `US-SUBSCRIPTION-CLI-AI-BRIDGE` / decision 0049.
- Cầu nối `apps/api/app/ai_cli_bridge.py` (thư viện chuẩn) chạy trên máy chủ dưới user service
  `business-ai-agents-ai-cli-bridge.service`, chỉ nghe `172.17.0.1:11436`, bắt buộc Bearer token
  (tệp trong `~/.config/business-ai-agents/`, vào container qua `.env`). Tối đa 2 lượt song song.
- Nhà cung cấp mới `claude_code`, `codex`, `antigravity` cho mọi tác vụ `complete_json` và chat
  đồ thị (gọi công cụ mô phỏng bằng JSON có cấu trúc, tên công cụ trong enum). Không nhận API key
  cá nhân. Runtime cục bộ mặc định Codex `gpt-6-luna` effort low; Claude `sonnet` low; agy
  `gemini-3.8-flash-medium`. Embedding RAG vẫn dùng Mistral.
- An toàn với nội dung không tin cậy: Claude Code chạy không có công cụ; Codex và Antigravity chạy
  trong bubblewrap chỉ thấy tệp đăng nhập của chính nó (Codex: đúng `~/.codex/auth.json`; agy:
  keyring qua `xdg-dbus-proxy --talk=org.freedesktop.secrets`), môi trường không có API key.
- Chế độ nhóm luôn tắt cầu nối: gói đăng ký là cá nhân, dùng chung cho nhóm là chia sẻ tài khoản.
- Quyết định đầy đủ: `docs/decisions/0049-subscription-cli-ai-bridge.md`.

## DEC-063 - Embedding qua Gemini API miễn phí (gemini-embedding-2)

- Ngày: 2026-10-24; Harness intake #12 / story `US-GEMINI-EMBEDDING-API` / decision 0050.
- Thêm `SEARCH_EMBEDDING_PROVIDER=gemini` (`gemini-embedding-2`, `GEMINI_API_KEY` trong header,
  1024 chiều Matryoshka, không migration). Mistral vẫn là mặc định và vẫn chọn được.
- Tiền tố truy hồi: tài liệu `title: none | text: …`, truy vấn `task: search result | query: …`
  (`embed()` và `embed_query()`). Tìm kiếm pgvector chỉ so hàng cùng `provider`/`model`.
- 429: chờ theo `RetryInfo` của Google, tối đa 20 giây mỗi lần thử lại.
- Gói miễn phí cho Google dùng nội dung để cải thiện sản phẩm (kể cả tài liệu tải lên khi RAG
  lập chỉ mục). Đổi model phải lập chỉ mục lại.
- Quyết định đầy đủ: `docs/decisions/0050-gemini-embedding-api.md`.
