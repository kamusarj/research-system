# Validation

## Proof Strategy

Prove the default local workflow remains compatible and enabled auth fails closed. Validate login,
session rotation/expiry/revocation, role hierarchy, owner-only operations, CSRF, cookie flags, generic
credential errors, audit attribution, file-mounted secrets and production configuration guards.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Password hashing; token hashing; production config validation; secret-directory precedence; route policy matrix. |
| Integration | Bootstrap/login/me/logout; inactive/expired/revoked session; CSRF; viewer/researcher/owner operations; user administration; actor audit. |
| E2E | Login/logout and role-visible controls on desktop/mobile; existing local-disabled suite remains green. |
| Platform | Migration round trip; API/frontend build; enabled Compose runtime with temporary provisioned owner and secure-default restore. |
| Performance | Login rate limit; session lookup uses unique token-hash index. |
| Logs/Audit | Password/session/CSRF/email markers absent from logs; successful/failed auth and privileged actor records present. |

## Fixtures

- Deterministic owner/researcher/viewer users with test-only passwords.
- Active, expired and revoked opaque sessions.
- Existing graph change, research and collector fixtures.
- Temporary secret directory containing non-production marker values.

## Commands

```text
cd apps/api && uv run ruff check app tests
cd apps/api && uv run python -m pytest -q
make verify-migrations
cd apps/web && npm run lint && npm run typecheck && npm test -- --run
E2E_BASE_URL=http://127.0.0.1:13000 npm run test:e2e
docker compose config --quiet
docker compose build api worker frontend
```

## Acceptance Evidence

Completed 2026-07-21:

- API lint and all 118 collected tests pass. Coverage includes Argon2/non-plaintext storage,
  opaque-session hashing/expiry/revocation, generic failures, login rate limiting, CSRF, route-role
  hierarchy, privileged user operations, actor attribution, secret-file precedence and production
  fail-closed settings.
- Web lint, TypeScript, optimized production build and 15 Vitest files/26 tests pass. Auth tests
  cover the enabled login gate, credentialed requests, trusted-local compatibility and viewer role.
- Migration verification upgraded from an empty database, found no model drift, downgraded the auth
  revision and upgraded to head `f3a6c8d1e204` again.
- Existing local-disabled browser regression passed 27/27 across desktop, tablet and mobile Chrome.
- Enabled-auth runtime proof passed 6/6 browser cases across those viewports: owner login/logout and
  viewer read-only control visibility. The proof used temporary users, raised only the proof login
  bucket from 5 to 20 for six parallel logins, then restored the default, local mode and runtime.
- API/worker/frontend images built; the base and secrets-overlay Compose configurations validate.
  The running local stack returned `ready`, 45 canonical nodes, 32 edges and valid graph invariants.
- The temporary accounts, sessions and proof audit rows were removed. A bounded API log scan found
  none of the proof identity, password-field, CSRF-header or cookie-name markers.

Known non-blocking warning: FastAPI TestClient reports Starlette's existing `httpx` deprecation
notice. TLS termination, external secret rotation/manager, OIDC/MFA and tenant isolation remain
explicitly outside this story.
