# Validation

## Proof Strategy

Prove security bounds and typed failures in unit tests, PDF behavior through API tests, UI lifecycle
with mocked blobs, and a real XeLaTeX CV compile rendered in Chrome.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | source cap, missing compiler, timeout, failed compile, PDF cap/success |
| Integration | compile endpoint returns PDF and typed errors |
| E2E | LaTeX Preview requests and embeds compiled PDF without horizontal overflow |
| Platform | real CV compiles with XeLaTeX and renders in Chrome |
| Performance | debounce and 20-second compiler timeout |
| Logs/Audit | source and raw compiler log are not persisted/logged |

## Fixtures

- Minimal standalone XeLaTeX document and deterministic fake PDF bytes.

## Commands

```text
Backend/frontend focused suites, production build, Docker rebuild, real Chrome smoke.
```

## Acceptance Evidence

- XeLaTeX API smoke produced a 12,376-byte PDF 1.7 using Noto Sans, Vietnamese and Font Awesome.
- Chrome imported a standalone two-column CV and displayed a compiled PDF blob in the enlarged
  Preview frame; the endpoint returned HTTP 200.
- Backend Ruff and all 301 backend tests pass. Frontend ESLint, TypeScript, all 103 tests, the
  14-route production build and 12/12 document Playwright cases pass.
- Docker API image rebuilt with XeLaTeX, LaTeX Extra, recommended/extra fonts and Noto; runtime
  health and a post-limit compile smoke pass.
