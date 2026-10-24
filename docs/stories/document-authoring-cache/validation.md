# Validation

## Proof Strategy

Prove cache parsing and identity scoping independently, then exercise the page
from restored draft through editing and successful creation. Existing upload
and preview tests prove server validation and non-executable rendering.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Format mapping, safe filename, versioned cache read/write/clear, corrupt and oversized cache rejection. |
| Integration | Page restores the current user's draft, writes edits immediately, retains on upload error and clears on success. |
| E2E | Live refresh preserves typed content; Create opens a real document workspace. |
| Platform | Production build and rebuilt frontend serve the authoring UI. |
| Performance | Authoring cache is bounded to two million characters. |
| Logs/Audit | No draft title/body in API, runtime or test logs. |

## Fixtures

- In-memory localStorage with separate owner/researcher keys.
- Markdown authoring draft.
- Mocked successful and failed upload responses.

## Commands

```text
cd apps/web && npm test -- --run
cd apps/web && npm run build
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
  docker compose up -d --build frontend
```

## Acceptance Evidence

- Cache helpers prove version validation, per-user key isolation, corrupt and
  oversized value rejection, explicit clearing and safe format/filename mapping.
- Three authoring component tests prove refresh restoration, immediate cache
  writes, governed upload creation, success-only clearing and failure retention.
- The full frontend suite passes 77/77; ESLint and sequential TypeScript checks
  pass.
- The production Next.js build passes with 14 routes.
- The existing backend Markdown upload integration test passes against the same
  `POST /api/v1/documents` contract used by authored files.
- The rebuilt runtime serves `/documents` on frontend `13000`; API health is
  `ok`, and database/API/worker/frontend are running.
- Playwright verifies the exact type → F5 → restore → discard → F5-empty
  workflow on desktop, tablet and mobile Chrome (3/3).
- An initial Playwright attempt could not write the root-owned repository
  `test-results/.last-run.json`; rerunning with an isolated `/tmp` output
  directory passed without changing repository permissions.
