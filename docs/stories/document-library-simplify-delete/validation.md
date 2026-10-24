# Validation

## Proof Strategy

Prove the list contract in component tests, the endpoint and cleanup guards in API tests, and the
owner policy in the route-policy matrix. Run frontend type/lint checks for the widened response type.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Summary normalization and fallback through serialization |
| Integration | Delete inactive document; reject active, intake-linked, and applied-graph documents |
| E2E | Uploaded-document list exposes editor action and four-column content |
| Platform | Responsive table retains readable actions and summary |
| Performance | List summary is derived from already-loaded local database records |
| Logs/Audit | Successful delete retains `document.deleted` without source content |

## Fixtures

- Local object storage with a Markdown upload.
- Deterministic extracted research content.
- Draft and applied document graph change sets.

## Commands

```text
scripts/verify_document_library_delete.sh
```

## Acceptance Evidence

- API: 38 focused tests passed.
- Frontend: 10 focused tests passed.
- Ruff and ESLint passed.
- Next.js production build compiled, type-checked, and generated all 15 routes.
- Playwright passed the uploaded-document editor/list flow at desktop, tablet, and mobile widths.
