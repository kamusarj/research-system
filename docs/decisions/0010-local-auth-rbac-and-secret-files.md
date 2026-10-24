# 0010 Local Auth, RBAC and File-Mounted Secrets

Date: 2026-07-21

## Status

Accepted

## Context

Gate C requires authenticated non-local exposure, but the current single-team app trusts every
caller. The architecture allows basic auth before SSO/Keycloak and already contains a user table.
Browser-held long-lived bearer tokens, proxy-only headers and environment-only secrets each leave an
avoidable security or operational weakness.

## Decision

Add an opt-in `local` auth mode based on Argon2 password hashes and random opaque server-side sessions
whose tokens are hashed in PostgreSQL. Browser sessions use HttpOnly/SameSite cookies plus explicit
CSRF validation. Enforce server-side role hierarchy `owner > researcher > viewer`; reserve canonical
publication/review/apply and user administration for owners. Bind the authenticated user ID into
audit/review provenance.

Keep trusted local mode disabled by default for current local acceptance, but make staging/production
configuration fail closed unless auth and Secure `__Host-` cookies are enabled. Allow settings to
read service-scoped secret files from `/run/secrets`, with direct environment values retained only for
local/backward-compatible operation.

## Alternatives Considered

1. JWTs in browser storage were rejected because server-side revocation and credential containment
   are more important than statelessness for this application.
2. Trusted proxy headers were rejected without an enforced private API boundary.
3. Bundled OIDC/Keycloak was deferred until an issuer/client and team SSO requirement exist.
4. UI-only roles were rejected because the API must remain authoritative.

## Consequences

Positive:

- Lost sessions can be revoked without rotating a global signing key.
- Passwords, session values and deployment secrets do not enter source control or durable logs.
- New API mutations inherit authenticated researcher access unless explicitly escalated; sensitive
  canonical operations are owner-only.
- Local development and existing acceptance fixtures remain reversible through `AUTH_MODE=disabled`.

Tradeoffs:

- PostgreSQL is required for login/session availability.
- Operators must provision the first owner through stdin and terminate TLS externally.
- Local password auth does not provide MFA, enterprise SSO or tenant isolation.
- Session cleanup and password/reset operations become explicit operator responsibilities.

## Follow-Up

- Add OIDC/Keycloak as a separate identity adapter when an issuer/client contract is approved.
- Add service-account credentials with scoped permissions before Discord Gate D.
- Define session cleanup cadence, incident response and secret rotation ownership for production.

