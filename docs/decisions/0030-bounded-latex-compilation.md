# 0030 Bounded LaTeX Compilation

Date: 2026-08-04

## Status

Accepted

## Context

The safe browser parser cannot reproduce arbitrary LaTeX templates. Overleaf-compatible output
requires a real TeX engine, but LaTeX is user-controlled executable input.

## Decision

Compile standalone sources ephemerally with XeLaTeX using `no-shell-escape`, a fresh temporary
directory, strict source/output/time/resource limits and no request-time network/package install.
Embed only the returned PDF. Keep the safe renderer as a failure fallback.

## Alternatives Considered

1. Expand regex mappings indefinitely.
2. Use a browser-only partial TeX implementation.

## Consequences

Positive:

- Preview matches the TeX engine for supported installed packages and fonts.
- Compilation failures become explicit rather than leaked source syntax.

Tradeoffs:

- API image size and build time increase because TeX Live is installed.
- Multi-file projects and missing assets remain unsupported.

## Follow-Up

- Move compilation to a dedicated sandbox service before untrusted multi-tenant deployment.
