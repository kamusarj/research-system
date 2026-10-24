# 0028 Document AI Proxy Budget and Simple Authoring

Date: 2026-08-03

## Status

Accepted

## Context

The document instant-edit provider can validly take longer than 30 seconds, while Next.js rewrite
proxying defaults to a 30-second timeout. A live DeepSeek request completed successfully at the API
after 33.8 seconds, but the browser-facing proxy had already reset the socket and displayed a
generic HTTP 500. The authoring page also repeats source content in a permanently expanded preview
and surrounds the primary editor with explanatory and policy panels.

## Decision

Set the browser-to-API proxy timeout above the configured 120-second AI request budget so one
request has one effective deadline. Preserve typed provider errors at the API boundary and map
transport/provider/no-change failures to localized editor feedback. Only transient failures expose
an explicit Retry action; retries remain user-triggered because provider calls can have cost.

Keep title, format, editable import, source editor, contextual AI, local cache status and explicit
Create/Save as the primary document workflow. Make safe Raw/Preview/Side-by-side inspection
collapsed by default during pre-create authoring, and remove duplicated prose and the separate
upload-policy card. PDF/DOCX upload and the document list remain available in a compact secondary
section.

## Alternatives Considered

1. Lower the AI timeout to 30 seconds: rejected because it would turn successful slower provider
   responses into failures.
2. Automatically retry every provider failure: rejected because calls can be costly and duplicate
   work; only the user may request another attempt.
3. Remove preview entirely: rejected because editable markup formats still require Raw, Preview and
   Side-by-side inspection.
4. Move AI editing into an asynchronous job: deferred because local instant edits are stateless and
   the aligned request budget is sufficient for the current MVP.

## Consequences

- Provider requests up to the configured AI budget can complete through the same-origin proxy.
- Unexpected malformed provider payloads return a typed 502 instead of an internal 500.
- Users see actionable localized feedback and can retry transient failures without reselecting.
- The default page is shorter and editor-led; detailed preview remains one click away.
- No database, source-version, RAG, graph, authorization or audit boundary changes.
