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
