# Design

## Domain Model

`NormalizedSource` remains the adapter boundary. Optional enrichment can replace a partial article or
PDF result only when it produces useful bounded text, and it must add provenance and explicit
limitations. A Reel transcript is user-supplied source evidence: ordered segments contain a
non-negative timestamp and bounded text, with a bounded total payload and an optional language.

`LinkSubmission.source_overrides` stores validated enrichment inputs separately from fetched source
data. Transcript bodies are not returned by list APIs or written to audit/application logs. A summary
(configured, language, segment count and update time) is safe to expose to the queue UI.

## Application Flow

1. The worker performs the current bounded public fetch and adapter extraction.
2. If an article is partial only because JavaScript content is missing and browser rendering is
   enabled, it renders once in an isolated Browserless context, reparses the bounded HTML and keeps
   the better result.
3. If a PDF has no usable text layer and OCR is enabled, the worker renders only the configured page
   budget and invokes Tesseract with a per-page timeout. URL PDFs and uploaded documents share the
   OCR service and provenance rules.
4. A researcher may add/replace a transcript only on an unapproved Facebook Reel/video submission.
   The command validates and stores the override, records metadata-only audit evidence, resets
   derived fields and requeues the submission.
5. Reprocessing overlays the transcript on public metadata, then runs the existing hash, dedupe,
   classification and review workflow. Approval remains owner-only.

## Interface Contract

- `PUT /api/v1/ingestion/links/{submission_id}/transcript`
- Request: optional language plus 1-500 ordered `{timestamp_seconds, text}` segments; maximum total
  transcript size is 120,000 characters.
- Response: the ordinary serialized submission with a transcript summary, never the stored body.
- Only researcher/owner roles may write. Non-Facebook sources, non-video Facebook sources, approved
  submissions and invalid ordering return typed 4xx responses.
- Browser/OCR failures surface typed limitation codes such as `BROWSER_RENDER_UNAVAILABLE`,
  `BROWSER_RENDER_FAILED`, `OCR_UNAVAILABLE` and `OCR_FAILED`; existing useful metadata survives.

## Data Model

An additive migration adds non-null JSON `source_overrides` with an empty-object default to
`link_submissions`. No existing row changes behavior. Downgrade removes only override data.

Transcript replacement is permitted only before approval and is fully reprocessed so content hashes
and classifications cannot become stale. Audit events contain actor, submission ID, language and
segment count, but not transcript text.

## UI / Platform Impact

The ingestion queue shows a compact transcript form only for a public Reel/video whose limitation is
`TRANSCRIPT_UNAVAILABLE` (or already has a user transcript) and only to researcher/owner roles. Lines
use `HH:MM:SS text`, `MM:SS text` or raw-second syntax and are parsed client-side before the typed API
call. The stored body is not echoed back after submission.

Browserless is an optional Compose profile with no published host port. The app connects using an
operator-provided token. OCR dependencies live in the shared API/worker image. Both features default
off so local startup and existing behavior remain compatible.

## Observability

Structured logs record adapter outcome, duration, typed code, page/request counts and output size,
but never fetched HTML, OCR text, transcript text, cookies, Browserless tokens or raw stderr. Audit
records cover transcript create/replace and retain only safe metadata. Provider counters distinguish
success, disabled, timeout, rejected-target and failure outcomes.

## Alternatives Considered

1. Rendering every article was rejected because it increases attack surface and cost; ordinary HTTP
   extraction remains first choice.
2. Letting Browserless access arbitrary resources was rejected; request interception reuses the
   public-target validator and blocks image/media/font downloads.
3. A Python OCR library with embedded native bindings was rejected in favor of the mature Tesseract
   CLI boundary with timeouts and no temporary files.
4. Automatic Reel media download/transcription was rejected because it would broaden authorization,
   privacy, platform-policy and compute scope. User-supplied transcripts preserve provenance.
5. Storing transcript text inside audit events was rejected because audit metadata is not a content
   store and should minimize sensitive payload replication.
