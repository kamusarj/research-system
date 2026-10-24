# Exec Plan

## Goal

Recover useful, reviewable evidence from JavaScript-rendered public articles, scanned PDFs and
user-supplied public Reel transcripts without weakening source-access, SSRF or publication controls.

## Scope

In scope:

- Optional Browserless rendering for otherwise-partial article sources.
- Optional bounded Tesseract OCR for scanned URL PDFs and uploaded PDFs.
- Validated, timestamped, user-supplied Reel/video transcript command and queue UI.
- Additive override migration, provenance, typed limitations, audit and metrics/log safety.
- Unit, integration, migration, browser, image and optional-service runtime proof.

Out of scope:

- Facebook authentication, private content, media download or automatic speech transcription.
- Paywall/anti-bot bypass and general-purpose browser automation.
- Replacing current direct-fetch or PDF text-layer extraction.
- Automatic publication.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- External systems and subprocesses.
- Public contracts.
- Cross-platform/deployment.
- Existing behavior.
- Multi-domain.

Hard gates:

- Browser SSRF containment.
- Bounded resource use.
- Transcript authorization and non-leakage.
- Human review remains mandatory.

## Work Phases

1. Confirm pipeline behavior, official provider/runtime contracts and risk boundaries.
2. Record high-risk story and durable architecture decision.
3. Implement additive schema, settings and isolated enrichment services.
4. Integrate URL/document workers, transcript API and role-aware queue UI.
5. Add negative SSRF/resource/auth/leakage tests and migration proof.
6. Run backend/web regression, E2E, image and optional-service runtime checks.
7. Update product docs, Harness evidence and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- Access requires login, private content, anti-bot/paywall bypass or media download.
- Existing content would need destructive migration.
- A browser request cannot be checked against the public-target policy.
- OCR/browser limits or human review would need to be weakened.
