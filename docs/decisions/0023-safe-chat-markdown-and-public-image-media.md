# 0023 Safe chat Markdown and public image media

Date: 2026-08-01; amended 2026-08-02

## Status

Accepted; narrows the asset exclusion in decision 0022.

## Context

The first shared-chat implementation intentionally replaced every image pointer with a placeholder
and rendered message text as a plain paragraph. The owner reported that this dropped images present
in a public share and exposed Markdown syntax instead of the formatted conversation.

## Decision

Render every chat message through `react-markdown` with GitHub-flavored Markdown support, raw HTML
disabled, and safe link components. Keep imported public images as structured `media_json`, not
inside provider-bound message text. Accept direct HTTPS pointers only on a small explicit OpenAI
asset-host allowlist. Resolve current `sediment://file_*` pointers only through ChatGPT's anonymous
shared-conversation asset endpoint using the same public share ID; never use account credentials or
login cookies. Validate the public peer, redirect hosts, raster MIME type and per-image/aggregate
byte limits before copying image bytes into local object storage.

Expose cached bytes through a bounded same-origin chat-media route, cap images per import, and
render them lazily with `referrerPolicy=no-referrer`. Do not import attachments, private file
pointers, authenticated assets or dynamically broaden the allowlist. An unavailable/non-public
pointer remains a visible placeholder. Existing sessions cannot recover discarded pointers and
must be re-imported.

## Consequences

- Markdown headings, emphasis, lists, quotes, tables, links and fenced code render correctly.
- Embedded HTML and scripts are not executed.
- Public OpenAI-hosted images visible in a share render from immutable local cached bytes; signed
  URLs and storage keys are not exposed to the AI provider or browser.
- A failed database commit removes any image objects written by that import.
- User-uploaded images that ChatGPT omits from the public share remain unavailable by design.
