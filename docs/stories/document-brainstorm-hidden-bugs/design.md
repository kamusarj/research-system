# Design

## Approach

Harden the existing browser boundary without new API contracts:

1. `normalizeDocumentSelection` rejects out-of-range or whitespace-only ranges.
2. `useDocumentInstantEdit.run` returns success boolean; chat routing maps to
   `ready | selection_required | failed | busy`.
3. Authoring and uploaded editors disable brainstorm send while instant-edit is busy and disable
   apply while a pending review exists.
4. Local-only assistant status messages explain ready/failed outcomes and are excluded from provider
   history and Apply actions.
5. Brainstorm apply checks standalone LaTeX integrity before mutating the local draft.

## Risks

- Over-blocking apply during pending review is intentional to prevent stale Accept.
- LaTeX apply guard may block intentional append of non-LaTeX notes; users should use explicit
  reviewed edit commands for structural changes.
