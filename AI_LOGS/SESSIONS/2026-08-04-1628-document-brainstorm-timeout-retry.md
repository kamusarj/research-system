# Session: Document Brainstorm Timeout Recovery

## Context

- User request: fix the `DeepSeek chat request timed out` error shown in Document Brainstorm.
- Agent: Codex
- Date/time: 2026-08-04 16:28 Asia/Bangkok

## Work Done

- Files changed: `apps/web/components/document-brainstorm.tsx`,
  `apps/web/components/document-authoring.test.tsx`, `apps/web/lib/i18n.tsx`,
  `Docs/Research System Implementation Plan.md`,
  `docs/stories/document-brainstorm-reliability/*`,
  `docs/decisions/0031-explicit-document-brainstorm-retry.md`, `AI_LOGS/HANDOFF.md`,
  `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, and this session log.
- Behavior changed: typed provider, rate-limit, invalid-response and transport failures now show
  localized stable feedback. Retryable failures preserve the exact failed question and
  pre-request history; explicit Retry uses the current source/selection without adding a duplicate
  visible user turn. No retry is automatic and no AI response mutates source without Apply.
- Commands run: Harness bootstrap/intake #48/story/DEC-044; runtime log correlation; focused and
  full frontend tests; backend brainstorm tests/Ruff; ESLint; TypeScript; production build; live
  Chrome timeout injection; real DeepSeek smoke through the frontend proxy; responsive Playwright;
  story verification/completion; Compose/health/log and whitespace checks.

## Reasoning / Decisions

- Decision: preserve the accepted 120-second provider and 125-second proxy budgets and make
  recovery explicit instead of extending the wait.
- Reason: telemetry showed DeepSeek timing out at 120.3 seconds while the proxy remained aligned;
  automatic retry can duplicate cost or remotely completed work.
- Alternatives considered: automatic retry, silent provider fallback and a longer deadline were
  rejected. DEC-044 records the durable behavior.

## Verification

- Tests/checks: backend brainstorm 4/4 and Ruff; frontend 104/104; ESLint; TypeScript; 14-route
  production build; document Playwright 12/12 across desktop/tablet/mobile; live Chrome injected
  timeout/retry proof; real DeepSeek LaTeX name-change request; health and recent runtime logs;
  Harness story verification and completion.
- Result: injected timeout displays no raw DeepSeek message, Retry makes the second request and the
  question remains visible exactly once. Real DeepSeek returned HTTP 200 in 3.3 seconds with the
  correct `NGUYỄN MINH AN` to `BÙI HOÀNG LINH` guidance. Story is implemented with all four proof
  flags passing. Intervention #16 records the owner correction and detailed trace #53 scores 3/3.

## Known Issues

- The first Playwright command could not overwrite container-owned
  `apps/web/test-results/.last-run.json` (`EACCES`). No existing artifact was deleted or changed;
  rerunning with a fresh `mktemp` output directory passed 12/12.
- Two initial Harness CLI invocations combined unsupported `--json`/proof arguments; commands were
  split according to CLI help and story verification/completion passed.

## Next Best Action

The owner can retry the retained question in the live Document Brainstorm panel. If DeepSeek has
another transient timeout, the localized notice and Retry action should appear without duplicating
the question or changing document text.
