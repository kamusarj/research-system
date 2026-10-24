# Graph Intelligence v2 Operations Runbook

## Purpose and boundaries

This runbook operates the local-first Graph Intelligence v2 stack. PostgreSQL is canonical;
document bytes live in the `document_objects` Docker volume; search and graph views are rebuildable
projections. The base Compose deployment defaults to trusted-local auth-disabled mode. Any shared,
staging or production deployment must enable local auth, secure cookies and HTTPS before exposure.

## Start and readiness

Port 8000 is occupied by another local project on the current host. Start this stack with:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
  docker compose up -d --build database api worker frontend
curl --fail http://localhost:18000/api/v1/health
curl --fail http://localhost:18000/api/v1/system/features
curl --fail http://localhost:18000/api/v1/system/readiness
docker compose exec -T api alembic current
```

## Workstation autostart

On the owner's workstation, install the tracked user-service unit and launcher. The launcher starts
from `$HOME/Desktop/Business AI Agents` by default; set `BUSINESS_AI_REPO_DIR` in the user-service
environment if the repository moves again:

```bash
install -Dm755 scripts/start_local_autostart.sh ~/.local/bin/business-ai-agents-autostart
install -Dm644 ops/systemd/user/business-ai-agents.service \
  ~/.config/systemd/user/business-ai-agents.service
systemctl --user daemon-reload
systemctl --user enable --now business-ai-agents.service
scripts/verify_local_autostart.sh
```

The launcher pins the Compose project name to `businessaiagents`, uses `--no-build`, preserves named
volumes, and starts only database, API, worker and frontend on `18000`/`13000`. It does not operate
on the separate Smart Exam Compose project at `8080`. Docker's `unless-stopped` policy handles
daemon restarts; the user service restores the stack after the desktop session begins.

`system/readiness` must return `status=ready` and `graph.valid=true`. Run the same invariant check
from the service environment with:

```bash
docker compose exec -T api python -m app.operations verify-graph
```

### Concurrent Knowledge Graph mode

The workstation autostart launcher and an explicit multi-user invocation use the tracked overlay:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
API_WORKERS=4 DATABASE_POOL_SIZE=4 DATABASE_MAX_OVERFLOW=2 \
  docker compose -f docker-compose.yml -f docker-compose.multi-user.yml \
  up -d --build database api worker frontend
scripts/verify_graph_multi_user.sh
```

This is process-level load balancing inside the API container: Uvicorn distributes connections to
four workers, each worker has a four-connection PostgreSQL pool plus at most two overflow
connections, and the frontend uses the standalone production server. Set worker/pool counts from
the real CPU and PostgreSQL connection budget; the worst-case API allocation is
`API_WORKERS × (DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW)`. Large JSON responses use gzip, and
approved graph reads carry `private, max-age=30, stale-while-revalidate=60`, so authenticated
responses are reusable only inside one browser and never as a shared public proxy object.

This overlay improves concurrent reads on one host; it is not permission to publish the local
auth-disabled service. Multi-host/container-replica production still needs TLS termination, an
external health-aware load balancer, shared Redis-backed rate limiting/cache invalidation and
aggregated metrics. Keep PostgreSQL as the canonical source of truth.

## Authentication and secret provisioning

Keep `AUTH_MODE=disabled` only for a trusted single-user machine. For a shared environment, set:

```env
AUTH_MODE=local
DEPLOYMENT_ENVIRONMENT=staging
AUTH_COOKIE_NAME=__Host-research_session
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
```

Provision the first owner before expecting browser login. The command reads the password from
standard input/getpass and never prints the email or credential in its success output:

```bash
docker compose exec api python -m app.operations create-user \
  --name "Research owner" --email owner@example.com --role owner --password-stdin
```

Reset a credential with `set-password --email ... --password-stdin`; this revokes that user's active
sessions. Owners can then manage active users and roles through `/api/v1/auth/users`. Do not weaken
secure cookies to make HTTP work outside local integration testing; terminate TLS first.

Application settings prefer matching files in `/run/secrets` over environment values. The
`docker-compose.secrets.example.yml` overlay shows service-scoped mounts for database, provider,
MinIO and metrics credentials. Set every required `*_SECRET_FILE` variable to a private host path
and start with both Compose files. Secret rotation and the backing secret manager remain operator
responsibilities; never store source files, passwords or tokens in the repository or `AI_LOGS`.

For the current DeepSeek graph-chat default, keep the value in a private host file and apply only
the dedicated overlay:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
DEEPSEEK_API_KEY_SECRET_FILE=/absolute/private/path/deepseek_api_key \
  docker compose -f docker-compose.yml \
    -f docker-compose.deepseek-secret.example.yml \
    up -d --no-deps --force-recreate api
docker compose exec -T api python -m app.operations verify-chat-provider
```

For a later narrow OpenAI rotation, set `GRAPH_CHAT_DEFAULT_PROVIDER=openai`, keep the replacement value in a private
host file with owner-only permissions and apply only the dedicated overlay. This does not require
provisioning every secret in the full managed-deployment example:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
OPENAI_API_KEY_SECRET_FILE=/absolute/private/path/openai_api_key \
  docker compose -f docker-compose.yml \
    -f docker-compose.openai-secret.example.yml \
    up -d --no-deps --force-recreate api
```

The file path must be outside the repository and must not be pasted into logs. The application reads
`/run/secrets/openai_api_key` before the legacy environment value, so the mounted replacement takes
precedence without editing `.env`.

After mounting a replacement OpenAI secret and recreating the API, run its explicit bounded provider
preflight before switching the default:

```bash
docker compose exec -T api python -m app.operations verify-openai
```

`verify-chat-provider` uses the configured default; `--provider openai|deepseek` selects explicitly.
The command makes one minimal provider request. OpenAI uses `store=false`; DeepSeek uses non-thinking
mode so private reasoning does not enter local history. It prints only provider/model,
typed readiness and booleans indicating whether response/request IDs and output were present; it
never prints the key, IDs, prompt, provider output or upstream error body. Exit `0` means the
credential/model project access is ready; exit `2` means the JSON error on stderr must be resolved.
This is a real, potentially billable provider call and is intended for explicit operator preflight,
not continuous health polling.

## Rollout flags

All flags default to enabled for local acceptance:

```env
GRAPH_V2_ENABLED=true
GRAPH_V2_DOCUMENTS_ENABLED=true
GRAPH_V2_CHAT_ENABLED=true
```

The master flag disables ontology, document workspaces, graph change sets, hierarchy queries and
chat with a typed `FEATURE_DISABLED` response while leaving the legacy relationship graph and
Research CRUD available. Sub-flags disable document or chat surfaces independently. Change flags in
`.env`, recreate API, and confirm `/api/v1/system/features` before acceptance testing.

Recommended staged rollout:

1. Enable v2 with chat disabled; accept upload, isolated graph, hierarchy and change review.
2. Replace/verify the OpenAI credential, enable chat, and run a scoped draft proposal.
3. Review metrics and audit events before exposing the workspace to more users.
4. Disable the affected sub-flag first if a serious workflow defect appears; preserve database data
   for diagnosis rather than downgrading migrations immediately.

## Rate and performance controls

The single-process local limiter protects costly mutations by client address:

| Bucket | Default per 60 seconds |
|---|---:|
| Document uploads | 10 |
| Analyze/retry | 10 |
| Chat turns | 30 |
| Graph apply | 10 |
| Login attempts | 5 |

Configure `RATE_LIMIT_*` and `RATE_LIMIT_WINDOW_SECONDS` in `.env`. A rejected request returns HTTP
429, `RATE_LIMITED`, `Retry-After` and `X-RateLimit-*` headers. Every normal API response includes
`X-Process-Time-Ms` and `Server-Timing`; requests at or above `API_SLOW_REQUEST_MS` are logged as
slow without logging request bodies or secrets.

The limiter is intentionally process-local. A multi-replica production deployment needs a trusted
gateway or shared Redis-backed limiter; local authentication does not provide tenant isolation.
With the four-worker overlay, configured per-process limits can allow up to roughly four times the
nominal bucket across evenly distributed requests, so do not treat them as global quotas.

## Correlated logs and metrics

Every API response returns `X-Request-ID`. A caller-provided value is preserved only when it matches
the bounded safe grammar; otherwise the API generates a UUID. API and worker logs use JSON lines and
an explicit field allowlist. Canonical request logs contain the method, route template, status and
duration, never the raw URL/query string, headers, body, document/chat content or exception message.
Default `httpx` and Uvicorn access logs are suppressed so they cannot bypass this rule. PostgreSQL
`AuditEvent` records remain the durable product audit source.

Prometheus exposition is disabled by default. Configure a dedicated scraper credential through the
deployment secret manager, not source control or `AI_LOGS`:

```env
LOG_FORMAT=json
METRICS_ENABLED=true
METRICS_BEARER_TOKEN=<dedicated-random-secret>
```

Scrape `GET /metrics` with a bearer header. The endpoint returns 404 while disabled, 503 if enabled
without a non-empty secret, and 401 for a missing/incorrect bearer value. Labels use bounded route
templates and typed outcomes; UUIDs, raw URLs and user content are not labels. Metrics are
process-local and reset on restart. The worker reports job outcomes in structured logs and exposes no
unauthenticated scrape server. Before production, separately provision TLS/network policy, secret
rotation, scrape retention, dashboards/alerts and any multi-replica aggregation.

## Evaluation and migration parity

```bash
make evaluate-graph-v2
make verify-migrations
docker compose exec -T api alembic check
```

The migration verifier creates a temporary SQLite database, upgrades to head, checks model parity,
downgrades one revision, upgrades again and requires the same head revision. Run PostgreSQL
`alembic check` as the production-dialect parity gate.

## PostgreSQL backup

Create a directory outside the repository with restricted permissions. Never add backups to Git or
`AI_LOGS`.

```bash
mkdir -p /path/to/private-backups
chmod 700 /path/to/private-backups
docker compose exec -T database pg_dump -U research -d research -Fc \
  > /path/to/private-backups/research-$(date +%Y%m%d-%H%M%S).dump
pg_restore --list /path/to/private-backups/research-YYYYMMDD-HHMMSS.dump >/dev/null
```

## Document-object backup

Quiesce writes before taking a consistent database-plus-object snapshot:

```bash
docker compose stop api worker
docker run --rm \
  -v businessaiagents_document_objects:/source:ro \
  -v /path/to/private-backups:/backup \
  alpine tar -C /source -czf /backup/document-objects-YYYYMMDD-HHMMSS.tar.gz .
docker compose start api worker
```

Record the database dump and object archive timestamps together. API keys remain environment
secrets and need a separate secret-manager backup; never place them in these archives intentionally.

## Legacy local-to-MinIO migration

This is a copy-and-verify operation, not a move. Keep the local object volume mounted throughout and
do not start until the production MinIO bucket, TLS/encryption, credentials, capacity and backup
policy are independently ready.

1. Quiesce writes and take matching PostgreSQL plus `document_objects` backups using the procedures
   above. Validate both archives, then restart the application.
2. Run the read-only inventory. It needs no MinIO credential and prints aggregate counts only:

   ```bash
   docker compose exec -T api python -m app.operations migrate-objects --mode plan
   ```

3. Stop if `clean` is false or if eligible/verified bytes do not match the maintenance inventory.
   Resolve missing files, declared-size differences, workspace hashes or reference mismatches; never
   fabricate replacement bytes or edit hashes to make the check pass.
4. Mount the managed MinIO credentials into the API service. Keep the local volume and database
   available. After explicit maintenance authorization, run:

   ```bash
   docker compose exec -T api python -m app.operations migrate-objects \
     --mode execute --confirm-copy-only
   docker compose exec -T api python -m app.operations migrate-objects --mode verify
   ```

5. Require `clean=true`, zero missing/invalid objects, matching migrated/verified counts and
   `deleted_objects=0`. Inspect `attachment.object_migrated` audit counts through the authorized
   audit process; application logs and CLI output intentionally omit keys and filenames.
6. Run document download and worker extraction smoke checks while MinIO is selected for reads/new
   writes. Repeat `plan` after an interruption; committed remote references are skipped and remaining
   local references are copied after the full remaining inventory passes.

The CLI commits one verified object at a time. A crash after an external copy but before the database
commit can leave an orphan remote object, but a rerun deterministically overwrites it from local and
verifies it. The command never deletes local files and provides no volume-cleanup mode. Local-volume
retirement requires a later independent authorization, successful `verify`, retained database/object
backups and an explicit retention decision. Migrated remote references do not silently fall back to
local if MinIO is unavailable.

## Restore drill

Test database dumps in a new database before touching the canonical one:

```bash
docker compose exec -T database createdb -U research research_restore_verify
docker compose exec -T database pg_restore --exit-on-error --no-owner \
  -U research -d research_restore_verify < /path/to/private-backups/research.dump
```

For an actual disaster restore, stop API/worker, restore PostgreSQL and the matching object archive,
run `alembic upgrade head`, start services, then require health, readiness, download, search, graph
and change-set smoke checks. Do not restore over the canonical database without an independently
verified backup and an explicit maintenance decision.

## Incident triage

- `FEATURE_DISABLED`: inspect rollout flags; this is expected during rollback.
- `RATE_LIMITED`: respect `Retry-After`; do not retry in a tight loop.
- `CHAT_PROVIDER_UNAVAILABLE`: verify server-side OpenAI credentials and provider access; never paste
  keys into chat or logs.
- `AI_RESPONSE_INVALID` during document-graph generation: the worker already makes one bounded
  same-provider recovery request for Pydantic schema/invariant validation failures. If the workspace
  still fails, inspect provider/model provenance and use the explicit manual retry control; do not
  assume an automatic provider switch occurred.
- `graph.valid=false`: disable graph apply, preserve the database, run `verify-graph`, and inspect the
  listed cycle/dangling/duplicate invariant before attempting compensation.
- Document `failed`: inspect the typed error and retry only when the provider/source failure is
  retryable. When optional OCR is enabled, scanned PDFs use the bounded PDFium/Tesseract path;
  otherwise `PDF_NO_TEXT_LAYER` remains an expected limitation.

## Acceptance evidence

Use `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`. Engineering automation can mark
technical gates, but only the product owner marks workflow acceptance.
