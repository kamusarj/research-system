# 0011 Bounded Source Enrichment Adapters

Date: 2026-07-21

## Status

Accepted

## Context

The public-source pipeline deliberately retains partial results for JavaScript-only articles,
scanned PDFs and Facebook Reel/video pages without transcripts. Gate C needs better extraction, but
unrestricted browser automation, unbounded OCR and automatic social-media download would weaken the
existing SSRF, resource, authorization and provenance boundaries.

## Decision

Keep direct public HTTP and PDF text-layer extraction as the primary paths. Add two opt-in,
fail-closed infrastructure adapters: Browserless rendering only for qualifying partial articles and
local Tesseract OCR only for scanned PDF pages. Validate every browser subrequest with the existing
public-target policy, block heavy resource types and bound render/OCR time, bytes and pages.

Allow a researcher to attach validated timestamped transcript evidence they already possess to an
unapproved public Facebook Reel/video submission. Store it as a source override, audit only safe
metadata, reprocess all derived data and preserve owner review before publication. Do not implement
Facebook login, private-media access, paywall/anti-bot bypass or automatic media transcription.

## Alternatives Considered

1. Always using a headless browser was rejected because direct extraction is cheaper, more
   deterministic and has a smaller attack surface.
2. Trusting only the top-level browser URL was rejected because scripts and redirects can request
   private-network resources.
3. Running OCR on all PDFs was rejected because valid text layers are more accurate and inexpensive.
4. Automatic Reel download/transcription was rejected pending a separate platform-policy,
   credential, privacy and compute decision.
5. Treating supplied transcript text as an audit payload was rejected to avoid unnecessary content
   duplication and leakage.

## Consequences

Positive:

- More partial public sources become useful while preserving typed provenance and human review.
- Both optional providers can fail without losing already-extracted metadata.
- Operators can leave the expanded attack/cost surface disabled unless the dependencies are ready.
- Transcript replacement cannot leave stale hashes or AI classification.

Tradeoffs:

- The shared worker image gains native OCR packages, and Browserless adds an optional service.
- DNS validation plus request interception reduces but does not eliminate infrastructure-level risk;
  production should also apply network egress policy.
- OCR quality depends on source resolution and installed language data.
- User-supplied transcripts require the user to have lawful access and retain source responsibility.

## Follow-Up

- Add production egress allow/deny policy and container resource limits before broad remote exposure.
- Evaluate automatic speech transcription only as a separate approved story with platform-policy and
  credential boundaries.
- Review OCR language packs and Browserless capacity from observed workloads.
