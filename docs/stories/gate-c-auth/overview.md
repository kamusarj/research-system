# Gate C Authentication, RBAC and Managed Secrets

## Current Behavior

The local-first application trusts every caller as the same local user. A `users` table exists but
has no credentials or sessions, mutation routes have no role checks, the browser has no login state,
and production credentials are normally injected as environment variables.

## Target Behavior

- `AUTH_MODE=disabled` preserves the trusted local workflow; `AUTH_MODE=local` enables authentication.
- Local auth uses Argon2 password hashes and random opaque sessions whose tokens are hashed at rest.
- Browser sessions use HttpOnly/SameSite cookies and CSRF tokens for state-changing requests.
- Active users have one of `owner`, `researcher`, or `viewer`; route policy is enforced server-side.
- Staging/production configuration refuses to start with auth disabled or insecure cookies.
- Authenticated actor IDs flow into durable audit records and governed graph review fields.
- Pydantic settings can read file-mounted secrets from `/run/secrets`; production guidance uses
  service-scoped Compose secret mounts instead of embedding credentials in images or source control.
- The frontend provides login/logout/current-user state and hides controls the active role cannot use.

## Affected Users

- Owners who manage users and approve canonical/published changes.
- Researchers who create and edit drafts, run analysis and propose governed changes.
- Viewers who inspect approved/current knowledge without mutation access.
- Operators provisioning credentials and enforcing HTTPS.

## Affected Product Docs

- `Docs/Research System Architecture Design.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`
- `README.md`

## Non-Goals

- Self-service registration, email reset, MFA, social login or a built-in identity provider.
- Multi-tenant/company row isolation.
- Service-account tokens for Discord or collectors.
- Claiming HTTPS, WAF, secret rotation or an external secret manager is bundled by the app.
- Migrating local users to OIDC/Keycloak in this story.

