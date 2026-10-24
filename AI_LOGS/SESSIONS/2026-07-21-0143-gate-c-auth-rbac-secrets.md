# Gate C Authentication, RBAC and Managed Secrets

## Context

- User request: set up Harness, set an active completion goal, read the existing AI logs and continue completing the Research System.
- Agent: Codex.
- Date/time: 2026-07-21 01:43 Asia/Bangkok.

## Work Done

- Files changed:
  - Added local auth schema/service/middleware/API/identity code, migration `f3a6c8d1e204`,
    password-stdin operations commands and auth tests under `apps/api/`.
  - Added auth/session/CSRF client state, bilingual login gate, identity/logout UI, role-visible
    controls, credentialed API requests and auth/E2E tests under `apps/web/`.
  - Added auth/deployment settings, `/run/secrets` file precedence,
    `docker-compose.secrets.example.yml`, safe defaults and ignored `.secrets/` content.
  - Added Harness story `US-GATEC-AUTH`, intake #7, decision 0010/DEC-023, validation evidence and
    operator/architecture/completion documentation.
  - Updated `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` and this session log.
- Behavior changed:
  - `AUTH_MODE=disabled` preserves trusted-local owner behavior; `AUTH_MODE=local` requires login.
  - Argon2 passwords and hashed opaque, expiring/revocable sessions back HttpOnly/SameSite cookies;
    unsafe authenticated requests require a session-bound CSRF cookie/header match.
  - Server route policy enforces `viewer < researcher < owner`; actor IDs now flow into durable
    audit and governed graph/review provenance.
  - Staging/production fail closed without local auth, Secure cookies and an `__Host-` session name.
  - Supported credentials prefer service-scoped files in `/run/secrets`; environment values remain
    a local-compatible fallback.
  - Frontend login/logout/current-user state works through the Next proxy and unavailable mutation
    controls are hidden while the API remains authoritative.
- Commands run:
  - Harness bootstrap/context queries, intake/story/decision operations and detailed trace #9.
  - Official FastAPI, Docker Compose secrets and OWASP cookie/CSRF guidance review.
  - OpenAI graph-chat application-path recheck; it returned typed `CHAT_PROVIDER_UNAVAILABLE`.
  - Ruff, Pytest, ESLint, TypeScript, Vitest, Next production build, migration parity, graph release
    evaluation, graph invariant CLI, Compose config/overlay validation and image builds.
  - Local-disabled 27-case Playwright matrix and enabled-auth six-case owner/viewer matrix.

## Reasoning / Decisions

- Decision: use local accounts with Argon2 hashes and opaque server-side sessions for the first
  single-team shared deployment.
- Reason: this fits the accepted local-first architecture, provides revocation/audit control and
  keeps a future OIDC boundary available without pretending an external identity provider exists.
- Decision: use an HttpOnly session cookie plus a readable, session-bound CSRF token rather than
  browser-local bearer tokens.
- Reason: the application is same-origin through the Next proxy and should not expose durable auth
  credentials to JavaScript storage.
- Decision: owners control user administration and canonical publish/review/apply actions;
  researchers create/edit/analyze/propose; viewers read/query only.
- Decision: file-mounted values override matching environment settings. The base environment path
  remains for trusted local compatibility; staging/production configuration is deliberately strict.
- Alternatives considered: OIDC/Keycloak, MFA, tenant isolation and a bundled TLS/secret manager
  were deferred because they expand the accepted MVP deployment boundary.

## Verification

- Tests/checks:
  - API: Ruff pass; all 118 collected Pytest tests pass.
  - Web: ESLint and TypeScript pass; 15 Vitest files/26 tests pass; optimized 15-route build passes.
  - Migration: empty upgrade/model parity/downgrade/upgrade passes at `f3a6c8d1e204`.
  - Browser: 27/27 local-disabled regression cases and 6/6 enabled-auth owner/viewer cases pass on
    desktop, tablet and mobile Chrome.
  - Platform: API/worker/frontend images build; base and secrets-overlay Compose configurations
    validate; graph evaluation and live invariant checks pass.
  - Runtime: restored to auth-disabled local mode; readiness is valid at 45 nodes/32 edges.
  - Security cleanup: temporary proof users/sessions and 23 proof-only audit rows were removed; the
    bounded log scan found none of the proof identity/password/CSRF/cookie markers.
- Result: Harness story `US-GATEC-AUTH` is implemented with all proof flags and detailed trace #9.

## Known Issues

- The configured OpenAI credential still fails through the real application path, so the scoped
  chat and final product-owner acceptance remain externally blocked; no acceptance was self-marked.
- The first six-way auth browser run correctly rate-limited the sixth parallel login at the default
  five attempts/minute. The final proof used a temporary threshold of 20, while a deterministic API
  test proves the unchanged default returns typed HTTP 429.
- TLS termination, external secret rotation/manager, OIDC/MFA, tenant isolation and multi-replica
  shared rate limiting remain deployment/follow-up work.
- FastAPI TestClient emits the existing Starlette/httpx deprecation warning.

## Next Agent Notes

- Continue from: OpenAI replacement/product-owner acceptance if the credential changes; otherwise
  take the optional OCR/browser-rendering and user-supplied Reel transcript slice next.
- Watch out for: do not enable Secure cookies over plain HTTP except with the explicit local proof
  override; do not add credentials to `.env`, the repository or AI logs.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
