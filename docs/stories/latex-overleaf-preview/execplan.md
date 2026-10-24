# Exec Plan

## Goal

Provide an Overleaf-like compiled PDF preview for standalone editable LaTeX documents.

## Scope

In scope:

- Bounded XeLaTeX compilation endpoint, PDF response, compile errors and embedded browser PDF.
- Fixed timeout, source/output limits, `no-shell-escape`, isolated temporary directory.

Out of scope:

- Arbitrary project files, network package installation and production multi-tenant compilation.

## Risk Classification

Risk flags: audit/security, external systems, public contracts, cross-platform, existing behavior.

Hard gates: execution of user-controlled LaTeX by a system process.

## Work Phases

1. Define security and API contract.
2. Implement bounded compiler and PDF viewer.
3. Add backend/frontend/E2E proof.
4. Build the runtime and verify a real CV document in Chrome.
5. Update Harness evidence and handoff.

## Stop Conditions

Pause if shell escape, network package installation at request time, persistence, or multi-file
upload becomes necessary.
