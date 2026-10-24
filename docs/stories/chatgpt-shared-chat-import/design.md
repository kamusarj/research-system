# Design

## Domain Model

`ChatSession` gains optional immutable import provenance: source type, canonical shared URL,
snapshot SHA-256, import timestamp and imported-message count. `ChatMessage.origin_type` is either
`local` or `chatgpt_shared`. Existing rows remain local.

`ChatMessage.media_json` stores a bounded list of display-only public image metadata and local
object references. Media stays separate from message text so provider history contains
conversation text but not signed asset URLs or object keys. Existing rows default to an empty
list.

A snapshot contains a title and an ordered, bounded list of visible `user`/`assistant` messages.
System, tool-addressed, reasoning and model-context records never cross the import boundary.

## Application Flow

1. Parse the submitted URL and accept only HTTPS, exact host `chatgpt.com`, one `/share/<id>` path,
   no credentials, port, query or fragment.
2. Resolve and connect only to public addresses, use only cookies issued by that anonymous share
   request, and follow only bounded redirects that still satisfy the exact ChatGPT share rule.
3. Stream at most the configured HTML byte limit and require HTML.
4. Decode the embedded public React loader payload, with legacy `__NEXT_DATA__` fallback.
5. Validate message roles, ordered count, total character and image-count bounds. Accept direct
   HTTPS image pointers only on the explicit OpenAI asset-host allowlist. Resolve generated-image
   `sediment://file_*` pointers only through the anonymous share asset endpoint.
6. Validate raster MIME/peer/redirect/byte bounds, cache images in object storage, then create the
   local graph-scoped chat session and imported messages atomically. Roll back cached objects when
   persistence fails, record safe aggregate audit metadata, and return `ChatSessionRead`.
7. Continue with the existing local-history provider loop. Imported source text is redacted and
   bounded by the same history/context rules before any cloud call.

## Interface Contract

```text
POST /api/v1/chat/imports/chatgpt
```

Request:

```json
{
  "url": "https://chatgpt.com/share/<conversation-id>",
  "provider": "deepseek"
}
```

The response is `201 ChatSessionRead` with additive provenance fields. Typed failures distinguish
invalid URL, unavailable/deleted share, oversized response, unsupported payload and empty snapshot.
No response contains provider cookies, raw HTML or hidden payload data.

## Data Model

An additive migration extends `chat_sessions` with `source_type`, `source_url`,
`source_snapshot_hash`, `source_imported_at` and `imported_message_count`, and extends
`chat_messages` with `origin_type`. Defaults preserve all existing rows as local. No existing data
is rewritten or deleted beyond the required default backfill. Follow-up migration
`f8b3d1e6a204` adds `media_json` with an empty-list default.

## UI / Platform Impact

`/chat` gains an Import shared chat action with URL and configured-provider fields. Imported
sessions and messages are labelled in desktop/tablet/mobile layouts. The source opens in a new tab
with safe link attributes. Chat text uses sanitized GitHub-flavored Markdown; public imported
images load from a bounded same-origin endpoint with lazy loading and `no-referrer`. Import is available only to users with researcher
mutation permission.

## Observability

The audit event contains only source type, snapshot hash and aggregate message/character counts.
Operational logs and metrics do not contain the URL, title, transcript or HTML. Typed error codes
remain safe for the UI.

## Alternatives Considered

1. Embed ChatGPT in an iframe: rejected because it does not provide a stable conversation contract
   and would not create locally controlled history.
2. Use a ChatGPT conversation/API identifier: rejected because public share IDs are not Responses
   or Conversations API IDs and there is no supported write-back contract.
3. Browser-cookie scraping: rejected because it would access private account state and create a
   credential/privacy boundary outside the approved product direction.
4. Snapshot import: selected because it is explicit, local, auditable and one-way.
