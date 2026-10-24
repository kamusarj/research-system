# Discord Knowledge-Gap Alerts

## Current Behavior

The Discord gateway already accepts allowlisted messages, submits their URLs and PDF
attachments through the source-neutral receipt API, and reports processing outcomes.
URL receipt items default to `auto_approve=false`, however, and receipt status does not
include the knowledge gaps related to an approved research item. A Discord user therefore
cannot complete or observe the intended intake-to-graph-to-gap workflow from the channel.

## Target Behavior

- Discord URL items request the existing guarded auto-approval path by default.
- The API still auto-approves only complete, high-confidence classifications. Partial
  sources, including Reels without transcripts, and low-confidence sources remain in
  review.
- Approval continues to create the governed ontology change set and also refreshes the
  persisted low-coverage gap projection.
- A namespace-scoped receipt read includes only active gaps related to that receipt
  item's approved research tags.
- The gateway reports those related gaps in its normal bilingual channel reply.

## Affected Users

- Researchers submitting public links in allowlisted Discord channels.
- Owners reviewing ontology change sets and operating the Discord gateway.

## Affected Product Docs

- `Docs/Business AI Agents Completion Goal.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Research System Architecture Design.md`
- `apps/discord-bot/README.md`

## Non-Goals

- Giving the bot graph mutation, approval, gap-management, or broad read scopes.
- Bypassing the confidence threshold, partial-source review, or ontology change-set review.
- Downloading or transcribing Facebook Reel media automatically.
- Adding a Discord credential or running against a real guild without owner-provided secrets.
