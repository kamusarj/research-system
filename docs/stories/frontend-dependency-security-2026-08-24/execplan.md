# Exec Plan — Frontend dependency security patch

## Goal

Remove every current high/critical npm audit finding from the frontend while preserving the existing
Next.js 15 application behavior and local runtime.

## Scope

In scope:

- Upgrade Next.js and `eslint-config-next` within the 15.5 Maintenance LTS line.
- Resolve vulnerable transitive `sharp`, `postcss`, and `nanoid` packages with bounded overrides.
- Run audit, dependency-tree, lint, type, unit, build, responsive browser and live-runtime proof.

Out of scope:

- Migrating to Next.js 16.
- Changing routes, APIs, auth, persisted data or public deployment posture.
- Claiming protection from the Next.js security release announced for 2026-08-26 before it exists.

## Risk Classification

Risk flags:

- Audit/security.
- Existing behavior.
- Public runtime dependency.
- Weak proof until browser/runtime regression completes.

Hard gates:

- Security dependency behavior.

## Work Phases

1. Confirm advisories and patched versions from npm and official Next.js sources.
2. Record the bounded Maintenance LTS decision.
3. Update manifest/lockfile.
4. Run static, unit, audit and production build checks.
5. Rebuild/recreate only the frontend and run responsive/live verification.
6. Update Harness evidence and handoff logs.

## Stop Conditions

Pause if the patch requires a Next.js major upgrade, weakens validation, changes public behavior, or
causes auth/data/API contract changes.
