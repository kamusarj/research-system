# Session Log

## Context

- User request: Brainstorm a Discord bot that watches an added channel and automatically sends GitHub, Facebook Reel, scientific-paper, PDF and other links into the Research System pipeline with no further sender action.
- Agent: Codex `/root`
- Date/time: 2026-07-15 16:35 Asia/Bangkok

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: None; this was architecture/product brainstorming only and no Discord or Research System code was implemented.
- Commands run: Read required AI logs, relevant completion/implementation/architecture documents, current ingestion schemas/services/source adapters, and official Discord message/Gateway documentation. Checked Markdown changes with `git diff --check` where available and direct file inspection.

## Reasoning / Decisions

- Decision: Preserve the accepted thin-adapter boundary. A future Discord Gateway listener should submit normalized URLs, attachment references and Discord provenance to the source-neutral Research API; it must not fetch/classify/publish content itself.
- Decision: Add a durable receipt/source-occurrence layer before the bot. Canonical URL jobs may remain deduplicated, but each `discord_message_id + normalized_url` occurrence needs its own idempotent provenance and notification state.
- Decision: A zero-step sender UX should use reactions/replies for queued, duplicate, completed, review and failed states. Zero-step capture does not imply that every low-confidence item is auto-published.
- Reason: The existing `link_submissions.url` uniqueness deduplicates processing but can lose later Discord occurrence metadata, and the existing API accepts one URL at a time without an explicit idempotency key or status callback.
- Alternatives considered: Put source extraction in the bot (rejected because it duplicates business logic); use slash commands/context menus (useful fallback but not zero-click); auto-publish every item (rejected because it bypasses existing confidence/review governance).

## Verification

- Tests/checks: No application tests were needed because no runtime code changed. Repository instructions and relevant source contracts were inspected; official Discord docs confirm passive message/attachment access depends on Message Content intent configuration.
- Result: Brainstorm is aligned with DEC-010/011/012 and keeps the unresolved runtime-stability audit as the current implementation priority.

## Next Agent Notes

- Continue from: Reproduce and fix the user-reported UI/runtime failures first. Once Gate C is accepted, convert this brainstorm into a Gate D product/API spec before implementation.
- Watch out for: PDF attachment URLs/bytes must survive async processing; current PDF adapter stops at `needs-text-layer`; current Facebook Reel adapter stops at `needs-transcript`; secrets and Discord tokens must remain outside the repo/logs.
- Suggested next command: `rg -n "class LinkSubmission|class LinkCreate|create_submission|source_ref" apps/api/app apps/api/tests`
