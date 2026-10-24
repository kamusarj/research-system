# Exec Plan

## Goal

Make the single-team Research System safe for authenticated non-local use with reversible local mode,
server-enforced roles and deployable file-mounted secrets.

## Scope

In scope:

- Additive user/session schema and migration.
- Argon2 password lifecycle and opaque revocable sessions.
- Cookie and CSRF controls.
- Owner/researcher/viewer route policy and audit actor attribution.
- Operator user provisioning and user-management API.
- Frontend login/session/role UX.
- `/run/secrets` settings support and Compose deployment example.
- Security, regression, E2E, migration and runtime proof.

Out of scope:

- OIDC/Keycloak, MFA, password email flows and public registration.
- Tenant isolation and service accounts.
- TLS termination implementation.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Data model.
- Audit/security.
- Public contracts.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Auth.
- Authorization.
- Audit/security.

## Work Phases

1. Confirm accepted security/deployment requirements and official practices.
2. Record story and durable architecture decision.
3. Implement schema, auth service, middleware and route policy.
4. Implement CLI provisioning, secret files and frontend session UX.
5. Add negative authorization/CSRF/cookie/session/migration tests.
6. Run full regression, E2E, image and enabled-runtime proof.
7. Update operations docs, Harness evidence and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- Multi-tenant data isolation becomes required.
- An external OIDC issuer/client is mandated instead of local auth.
- Existing product data would need destructive migration.
- Validation or cookie protections would need to be weakened.

