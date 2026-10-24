# Validation

## Proof Strategy

Prove optional enrichment is disabled-compatible, fail-closed and bounded. Browser proof must cover
every subrequest rather than only the initial URL. OCR proof must cover page, time and output limits,
no-text fallback and provenance. Transcript proof must cover validation, role enforcement,
reprocessing, audit minimization and human approval.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | URL/request interception; browser size/timeout; OCR page/time/text budgets; segment parser/order/size; provenance and limitation mapping. |
| Integration | Article render fallback; URL/upload scanned PDFs; transcript replace/requeue/dedupe/classify; role and approved-state denial; audit/log non-leakage. |
| E2E | Researcher adds a transcript; viewer cannot mutate; owner still reviews; responsive queue states. |
| Platform | Migration round trip; API/worker/frontend image build; disabled default; optional Browserless and Tesseract runtime smoke. |
| Performance | One render per qualifying job; blocked heavy resource types; OCR page cap and subprocess timeout. |
| Logs/Audit | No HTML/OCR/transcript/token/stderr bodies; safe outcome counters and metadata-only transcript audit. |

## Fixtures

- Static public-article HTML with and without JavaScript-only content.
- Browser request routes targeting public and private/loopback addresses.
- Small generated scanned PDF and mixed/no-text PDFs.
- Public Facebook Reel/video metadata with deterministic transcript segments.
- Owner, researcher and viewer identities in enabled-auth tests.

## Commands

```text
cd apps/api && uv run ruff check app tests
cd apps/api && uv run python -m pytest -q
make verify-migrations
cd apps/web && npm run lint && npm run typecheck && npm test -- --run && npm run build
E2E_BASE_URL=http://127.0.0.1:13000 npm run test:e2e
docker compose config --quiet
docker compose --profile browser config --quiet
docker compose build api worker frontend
```

## Acceptance Evidence

Completed 2026-07-21:

- API Ruff and all 125 backend tests pass. Focused extraction coverage proves browser subrequest
  denial, heavy-resource blocking, direct-first fallback, OCR page/pixel/time/output boundaries,
  URL/upload OCR provenance, transcript ordering/size/source/state rules, reprocessing and API/audit
  body non-leakage.
- The additive `source_overrides` migration upgrades from empty, has no model drift, downgrades one
  revision and upgrades to head `0b7d2e4f6a18` again.
- Web ESLint, TypeScript, optimized build and 15 Vitest files/28 tests pass. The complete local E2E
  matrix passes 30 tests on desktop/tablet/mobile Chrome (six enabled-auth-only cases skipped),
  including a new timestamped Reel transcript flow whose body is not echoed after save.
- API, worker and frontend images build. The API image contains Tesseract 5.5.0 with `eng`, `vie` and
  `osd`; an in-memory generated scanned PDF was read correctly through the actual PDFium/Tesseract
  service (`OCR_OK`, one page, 27 characters).
- The optional Browserless service is internal-only and pinned to
  `sha256:9e48bf8df71ba285f974dd9bd9effb59ce8a1e767cfe734b36a24b065ab033f4`.
  A disposable Compose profile returned `/pressure` 200 and Playwright rendered public
  `example.com` (`BROWSER_RUNTIME_OK`, one request, 559 bytes); the service stayed up after the
  probe and its temporary container was removed.
- Base and browser-profile Compose configurations validate. The restored default runtime has OCR
  and Browserless disabled, returns `ready`, and verifies 45 graph nodes/32 edges with no invariant
  errors on host ports 18000/13000; unrelated `smart_exam_*` containers were not changed.
- JSON logs and Prometheus metrics use bounded outcome labels/counts and exclude fetched HTML, OCR
  output, transcript bodies, subprocess stderr and Browserless tokens. Transcript audit records
  contain only actor, language and segment count.

Operational note: pulling the large Browserless image initially exhausted Docker storage. Exactly
6.582 GB of rebuildable unused build cache was pruned; no image, container volume or product data
was deleted. Root storage now has about 2.6 GB free, so operators should reclaim or expand Docker
storage before further large image upgrades.
