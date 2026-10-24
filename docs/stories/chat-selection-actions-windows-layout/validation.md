# Validation

## Proof Strategy

Prove selection ownership and explicit submission at component level, then use real Chromium text
selection at Windows desktop/laptop, tablet and mobile viewports. Verify that document selection
still creates a proposal rather than an immediate edit and that chat selection only prefills the
composer before Send.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Selection popover appears; chat action quotes text and does not call send; document action preserves existing proposal/Accept flow. |
| Integration | Existing chat/document clients and provider requests remain unchanged. |
| E2E | Native chat/message and textarea selection; visible actions; explicit Send/Accept; no page horizontal overflow. |
| Platform | Windows 1366×768 and 1920×1080 plus tablet/mobile responsive layout and production build. |
| Performance | Chat selection quote and composer remain bounded by existing 12,000-character contract. |
| Logs/Audit | No selection content is logged or persisted before explicit Send/Accept. |

## Fixtures

- Deterministic Markdown document and chat messages with selectable text.
- Existing mocked chat/document APIs and configured provider metadata.

## Commands

```text
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run
cd apps/web && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-chat.spec.ts e2e/document-upload.spec.ts
```

## Acceptance Evidence

- ESLint and TypeScript pass; focused shell/chat/document component coverage passes 7/7 and the
  complete frontend suite passes 84/84.
- Next.js production build passes with all 14 routes.
- Playwright passes 15/15 document/chat cases across desktop, tablet and mobile. Native text
  selection exposes visible actions; chat Ask AI fills the composer without a POST; document AI
  still requires proposal review and Accept.
- The desktop case additionally verifies 1366×768 and 1920×1080 Windows-style viewports: composer
  remains in viewport and document width never exceeds viewport width.
- Live Chrome screenshots visually confirm both chat and document popovers next to the selection;
  session history has no horizontal scrollbar and the redundant right rail is absent.
- Rebuilt frontend, direct/proxied health and `/chat` return HTTP 200; fresh API/frontend logs contain
  no error/exception/traceback/fatal/HTTP 500 pattern.
