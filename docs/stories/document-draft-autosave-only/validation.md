# Validation

## Proof Strategy

Prove that authoring edits are still written synchronously and restored after a
component remount, that no manual discard action is rendered, and that only a
successful Create clears the cache. Retain the existing failure-path proof.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Component writes every edit, restores after remount and exposes no discard control. |
| Integration | Failed Create retains cache; successful governed Create clears it and navigates. |
| E2E | Type, refresh, navigate away/reopen, restore, and confirm no discard action. |
| Platform | Production frontend build succeeds. |
| Performance | Synchronous bounded write path and two-million-character limit remain unchanged. |
| Logs/Audit | No draft body/title is logged or sent before explicit Create. |

## Fixtures

- Identity-scoped JSDOM `localStorage` for `owner-one`.
- English local runtime document authoring flow.
- Mocked successful and failed upload responses.

## Commands

```text
cd apps/web && npm test -- --run components/document-authoring.test.tsx lib/documents.test.ts
cd apps/web && npm run lint
cd apps/web && npx tsc --noEmit
cd apps/web && npm run build
```

## Acceptance Evidence

- Focused Vitest passes 24/24 across the authoring component and cache helpers.
- Full frontend Vitest passes 31 files / 138 tests.
- ESLint and `tsc --noEmit` pass.
- The Next.js production build passes all 15 generated routes.
- Rebuilt live runtime returns HTTP 200 for `/documents`; proxied health is `ok`
  and readiness remains valid at 45 canonical nodes / 32 edges.
- Focused Playwright passes 3/3 on desktop, tablet and mobile Chrome: type,
  refresh, navigate away, reopen, restore exact content, and find zero manual
  discard controls.
- Fresh API/worker/frontend log scan contains no error signature.
