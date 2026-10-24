# Design

## Domain Model

`User` gains an optional Argon2 `password_hash`, role constraint, password-change timestamp and
failed-login lock fields. `AuthSession` stores only SHA-256 hashes of a cryptographically random
session token and CSRF token, plus expiry/revocation timestamps and its user foreign key. Plaintext
passwords and session tokens are never persisted or logged.

Role hierarchy:

| Role | Capability |
| --- | --- |
| viewer | Authenticated read/query operations and explicitly read-only POST queries. |
| researcher | Viewer capabilities plus draft/content creation, editing, analysis, chat and proposal operations. |
| owner | Researcher capabilities plus publication/rejection/archive, collector approval, graph review/apply/compensation, training governance and user administration. |

The application remains single-team: all roles see the same workspace. Row-level tenancy is out of scope.

## Application Flow

1. An owner is provisioned through an operator CLI that reads the password from stdin.
2. Login verifies the normalized email and Argon2 hash using a generic error response.
3. Success rotates to a new opaque session, sets the HttpOnly session cookie and readable CSRF
   cookie, and records a durable audit event.
4. Authentication middleware resolves the hashed session, rejects inactive/expired/revoked sessions,
   binds actor/role context, and enforces the route policy before application logic runs.
5. Cookie-authenticated state-changing requests must send the CSRF cookie value in `X-CSRF-Token`.
6. Logout revokes the server-side session and expires both cookies.
7. Owner password reset/deactivation revokes all target-user sessions.

## Interface Contract

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET/POST /api/v1/auth/users` (owner)
- `PATCH /api/v1/auth/users/{user_id}` (owner role/active/name/password management)

When auth is enabled, unauthenticated protected calls return 401 `AUTH_REQUIRED`; insufficient roles
return 403 `ACCESS_DENIED`; missing/invalid CSRF returns 403 `CSRF_REQUIRED`. Health remains public.
Metrics retains its independent bearer boundary and is never authorized by a human session.

## Data Model

One additive migration alters `users` and creates `auth_sessions`. Existing user rows remain but
cannot log in until an owner provisions a password. Downgrade removes only auth-session data and new
credential fields; it does not delete users or product data.

## UI / Platform Impact

When auth is enabled, the frontend gates the application behind a bilingual login screen, fetches
`/auth/me`, includes credentials and a CSRF header in all mutations, exposes role identity/logout in
the shell, and hides owner/researcher controls based on capability. Backend enforcement remains
authoritative. Local mode remains unchanged when auth is disabled.

Production configuration uses `DEPLOYMENT_ENVIRONMENT=production`, `AUTH_MODE=local`, secure
`__Host-` cookie naming, HTTPS and file-mounted `/run/secrets` values. A separate example Compose
override documents service-scoped mounts without requiring secret files for local startup.

## Observability

Auth logs contain typed action/outcome and actor ID only after successful resolution; they never log
email, password, cookies, CSRF values or hashes. Durable `AuditEvent` rows cover login/logout, user
administration and privileged governed actions. Rate limiting protects login attempts independently.

## Alternatives Considered

1. Browser-stored JWT/bearer tokens were rejected because revocation and safe browser storage are
   weaker for this local-first UI.
2. Trusted reverse-proxy identity headers were rejected because direct API reachability could bypass
   the proxy unless a stronger network identity contract is added.
3. Bundled Keycloak/OIDC was deferred: the architecture explicitly treats SSO as an upgrade after
   basic team auth, and no issuer/client contract is configured today.
4. Auth-only UI hiding was rejected because authorization must be enforced server-side.

