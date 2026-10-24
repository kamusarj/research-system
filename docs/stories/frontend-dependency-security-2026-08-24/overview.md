# Frontend dependency security patch

## Discovered Behavior

The frontend is on Next.js 15.5.20. Fresh `npm audit --omit=dev` reports four high-severity findings
through Next.js and its `sharp`, `postcss`, and `nanoid` dependency chain.

## Target Behavior

The application remains on the supported Next.js 15.5 Maintenance LTS line with current patched
dependencies, and npm reports zero high or critical production findings.

## Implemented Result

The locked graph resolves Next.js 15.5.23 and patched direct/transitive dependencies. Both full and
production-only npm audits report zero vulnerabilities, and the rebuilt local runtime passes the
full static, unit, build and responsive browser regression suite.

## Affected Users

- Local owner.
- Any future researcher/viewer if this trusted-local runtime is later deployed under the documented
  auth/TLS controls.

## Affected Product Docs

- `README.md`
- `apps/web/package.json`
- `apps/web/package-lock.json`

## Non-Goals

- No feature or visual redesign.
- No Next.js 16 migration.
- No change to application API, authentication or database behavior.
