# Validation — Frontend dependency security patch

## Proof Strategy

Prove both dependency resolution and unchanged application behavior. Audit success alone is
insufficient; the production build, browser matrix and rebuilt live runtime must also pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Full 145-test frontend Vitest suite. |
| Integration | ESLint, TypeScript and Next.js production build. |
| E2E | Existing Playwright suite at desktop/tablet/mobile against port `13000`. |
| Platform | Rebuilt frontend image, health/readiness/routes and clean current logs. |
| Performance | No new route overflow or browser failure in responsive suite. |
| Logs/Audit | Zero high/critical npm audit findings; exact patched dependency tree recorded. |

## Fixtures

- Existing deterministic frontend unit and Playwright fixtures.
- Current local runtime with PostgreSQL data preserved.

## Commands

```text
cd apps/web && npm audit --omit=dev --audit-level=high
cd apps/web && npm ls next eslint-config-next sharp postcss nanoid
cd apps/web && npm run lint && npm run typecheck && npm test && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npm run test:e2e
```

## Acceptance Evidence

- `npm audit --audit-level=high` and `npm audit --omit=dev --audit-level=high` both report zero
  vulnerabilities.
- The resolved tree contains Next.js / `eslint-config-next` 15.5.23, `sharp` 0.35.3, `postcss`
  8.5.26, `nanoid` 3.3.18, `js-yaml` 4.3.1 and patched `brace-expansion` 1.1.18 / 5.0.9.
- ESLint, TypeScript, 33 Vitest files / 145 tests and the 15-route production build pass.
- Playwright passes 69 enabled desktop/tablet/mobile cases; six auth-only cases are expected skips
  in local auth-disabled mode.
- The frontend Dockerfile installs strictly from the lockfile. Production startup validates both
  production and development dependencies in the persistent volume and runs a deterministic
  `npm ci --include=dev` only when stale.
- The rebuilt/recreated live frontend is healthy on `13000`, all eleven primary routes and the API
  proxy return HTTP 200, and current startup logs contain no application error.
