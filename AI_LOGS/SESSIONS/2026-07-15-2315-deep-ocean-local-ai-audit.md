# Session Log

## Context

- User request: audit and optimize the UI, change its color tone, repeatedly test backend/frontend behavior, add and test a local model if possible, and live-test arbitrary GitHub/Facebook Reel/article/PDF URLs without downloading source files. Live AI tests were restricted to Mistral, DeepSeek and local models.
- Agent: Codex
- Date/time: 2026-07-15 23:15 Asia/Bangkok

## Work Done

- Files changed: `apps/web/app/globals.css`, graph theme, app icon, intake provider UI/types/translations, Playwright spec, `apps/api/app/ollama_bridge.py`, AI and ingestion services, provider/bridge/ingestion tests, Compose/environment examples, README, decisions and AI handoff logs.
- Behavior changed: the UI uses a WCAG-AA deep-ocean palette; desktop intake rows scroll within a bounded queue; Ollama availability is visible; local structured output is reliable; upstream provider failures become typed safe ingestion errors; an optional allowlisted bridge connects Docker to the existing host Ollama.
- Commands run: provider probes from the API container; live source submissions and polling; `make test`; `make lint`; `make build`; Playwright E2E; base/local-AI Compose validation; health/route/log/artifact checks; `git diff --check`.

## Reasoning / Decisions

- Decision: use navy, teal and indigo with a pale blue-gray canvas, preserving the established workspace structure while improving visual hierarchy and contrast.
- Reason: the prior warm palette was functional but the user explicitly requested a new tone; the new tokens pass the checked WCAG AA pairs and remain consistent across the graph and application shell.
- Decision: bridge to the already-installed host `qwen3.5:4b` through a narrow optional service rather than download a duplicate model or run a privileged Docker integration.
- Reason: this keeps local inference explicit and bounded. Only tags/version/generate are exposed, request size is capped, and model pulls are rejected.
- Decision: treat a public Reel with metadata but no transcript as `partial_success`/`TRANSCRIPT_UNAVAILABLE`.
- Reason: the system must not pretend classification succeeded or bypass Facebook access controls when useful public text is unavailable.

## Verification

- Tests/checks: Pytest 38 passed; Ruff passed; Vitest 12 passed; ESLint and TypeScript passed; Next.js production build passed; Playwright 12 passed across desktop/tablet/mobile; both Compose configs and `git diff --check` passed.
- Result: direct/proxied health are OK; all eight primary routes return 200; recent service logs contain no error/exception/traceback; no PDF/MP4/WebM appeared under `apps/`.
- Live providers: Mistral `mistral-large-latest`, DeepSeek `deepseek-v4-pro`, and Ollama `qwen3.5:4b` all returned valid structured output.
- Live sources: GitHub + DeepSeek, Python.org article + Ollama, and direct text-layer PDF + Mistral completed; Facebook Reel + Mistral safely returned metadata-only partial success with `TRANSCRIPT_UNAVAILABLE`.

## Known Issues

- Host Ollama must remain running for local inference; the bridge is local-development infrastructure, not a production gateway.
- Private/region-locked Facebook content and Reels without a public transcript cannot be fully classified without an authorized transcript/media adapter.
- Pytest still reports one upstream Starlette/httpx TestClient deprecation warning.

## Next Agent Notes

- Continue from: product-owner visual acceptance, then occurrence/receipt and attachment-storage design before Discord implementation.
- Watch out for: preserve user changes in the already-dirty worktree; do not touch `smart_exam_*`; never write provider keys to logs.
- Suggested next command: `docker compose --profile local-ai ps`
