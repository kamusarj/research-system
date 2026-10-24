# Gate C Bounded Source Enrichment

## Current Behavior

The source pipeline safely fetches public URLs and preserves partial results, but it cannot recover
article bodies rendered only by JavaScript or text from scanned PDFs. Public Facebook Reel/video
metadata is retained without a transcript, and there is no governed way for a researcher to attach
a transcript they already possess.

## Target Behavior

- An opt-in Browserless adapter may render public article pages after ordinary extraction reports
  `JS_RENDER_REQUIRED`; every browser request remains subject to the public-URL/SSRF policy and
  resource limits.
- An opt-in OCR adapter may recover text from bounded scanned-PDF pages using local Tesseract, while
  recording engine, language, page and limitation provenance.
- A researcher may attach or replace a timestamped, user-supplied transcript on a public Facebook
  Reel/video submission before publication. The worker reprocesses it through the existing dedupe,
  classification and human-review pipeline.
- Disabled, unavailable or failed enrichment preserves the current partial result and emits a typed
  limitation; it never fabricates content or auto-publishes it.

## Affected Users

- Researchers importing JavaScript-rendered articles, scanned PDFs and public Reel/video metadata.
- Owners reviewing enriched submissions before publication.
- Operators enabling Browserless/Tesseract and setting bounded runtime controls.

## Affected Product Docs

- `Docs/Source Processing Pipeline.md`
- `Docs/Research System Architecture Design.md`
- `Docs/Research System Completion Plan.md`
- `README.md`

## Non-Goals

- Logging into Facebook, fetching private media, bypassing anti-bot controls, paywalls or access rules.
- Downloading or transcribing Reel audio/video automatically.
- General browser automation, arbitrary script execution or browser access to private network targets.
- OCR of every text-bearing PDF, handwriting recognition or guaranteed OCR accuracy.
- Publishing enriched content without the existing human approval step.
