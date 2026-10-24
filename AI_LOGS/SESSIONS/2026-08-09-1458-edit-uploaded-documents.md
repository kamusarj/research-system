# Edit Uploaded Documents

## Context

- User request: make uploaded documents viewable and editable in Document workspace.
- Agent: Codex.
- Date/time: 2026-08-09 14:58 +0700.

## Work Done

- Files changed:
  - Backend document content/version/original-download services and contracts.
  - Frontend Document editor, original viewer, bilingual copy, styling and responsive E2E coverage.
  - Focused backend/frontend tests, story/decision/product docs and AI handoff logs.
- Behavior changed:
  - Readable PDF/DOCX uploads now expose canonical extracted text in the existing editor.
  - Original binary version 1 remains immutable and separately viewable/downloadable.
  - Saved binary-workspace edits are UTF-8 derivative versions and are processed/indexed as text.
  - Restoring original version 1 creates a new extracted-text derivative instead of replacing the
    editor with binary bytes.
- Commands run:
  - Harness bootstrap, intake #57, story/decision/update/complete commands and matrix queries.
  - Focused and full Pytest/Ruff/Vitest/ESLint/TypeScript/build proof.
  - Document Playwright suite across desktop/tablet/mobile.
  - Compose recreate, health/readiness/content/original endpoint checks and live Chrome DOCX check.

## Reasoning / Decisions

- Decision: preserve PDF/DOCX byte originals and edit only a clearly labelled extracted-text
  derivative under immutable versioning.
- Reason: this satisfies content curation without corrupting file types or falsely claiming layout
  fidelity.
- Alternatives considered: plain-text binary overwrite was rejected for data loss/type confusion;
  a full layout-faithful Office/PDF engine remains optional future scope.

## Verification

- Tests/checks:
  - Backend 313/313 full tests and 23/23 focused document tests; Ruff.
  - Frontend 118/118 tests; ESLint; TypeScript; 14-route production build.
  - Playwright Document suite 21/21 across desktop/tablet/mobile.
  - Live existing-DOCX read-only proof: 40,222 editor characters, derivative disclosure, original
    link, zero horizontal overflow; no user document was modified.
  - Runtime readiness `ready`; graph valid at 45 nodes / 32 edges.
- Result: pass. Harness story completion passed fresh proof.
- Harness: detailed trace #58 meets the required high-risk tier 3/3.

## Known Issues

- PDF/DOCX edits update AI-readable content, not original page/Office layout. Same-format layout
  export needs a separate product decision and editor/conversion design.
- The first unscoped backend test command hit two existing namespace imports; the required
  `PYTHONPATH=.` invocation passed all 313 tests and is now in the story verifier.
- Existing Playwright output under the repo is root-owned; proof used explicit writable `/tmp`
  output directories.

## Next Agent Notes

- Continue from: live frontend `http://localhost:13000/documents`.
- Watch out for: binary `source_version=1` is the immutable original; later binary-workspace versions
  are UTF-8 derivatives. Do not route those later versions back through PDF/DOCX parsers.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
