# Validation

## Proof Strategy

Prove deterministic intent routing, no advisory call for edit commands, exact range/instruction
forwarding, unchanged source before Accept, full diff visibility, Reject safety and Accept behavior.
Preserve ordinary brainstorm and responsive document workflows.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Vietnamese/English edit imperative detection; question remains advisory. |
| Integration | Existing structured instant-edit endpoint/range/revision validation. |
| E2E | Send rename command, inspect full diff, Reject/Accept; ordinary brainstorm unchanged. |
| Platform | Pre-create and uploaded editors; desktop/tablet/mobile. |
| Performance | One provider call per Send; no classification call. |
| Logs/Audit | Routed operation is instant edit; source/instruction bodies remain absent. |

## Fixtures

- LaTeX CV containing `NGUYỄN MINH AN` and rename instruction `sửa tên thành Bùi Hoàng Linh`.
- Deterministic instant-edit patch double.
- Existing advisory brainstorm double.

## Commands

```text
cd apps/api && .venv/bin/python -m pytest -q tests/test_document_instant_edit.py tests/test_document_brainstorm.py
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- Authoring component proof routes `sửa tên thành Bùi Hoàng Linh` to one custom instant-edit call,
  never calls advisory Brainstorm, renders complete original/replacement content, leaves the source
  unchanged before Accept and applies only after Accept.
- Uploaded-editor proof targets the exact native selection and proves Reject preserves source.
- Live Chrome against the rebuilt frontend recorded two edit calls and zero brainstorm calls across
  explicit Reject then Accept: Reject retained `NGUYỄN MINH AN`; Accept produced
  `BÙI HOÀNG LINH`. Pending review scrolls into view.
- A real DeepSeek call through the frontend proxy returned HTTP 200 in 11.4 seconds with a complete
  LaTeX replacement and `auto_apply_allowed=false`.
- Focused component tests pass 17/17. Full frontend tests pass 106/106; ESLint, TypeScript and the
  14-route production build pass. Focused backend instant-edit/brainstorm tests pass 11/11 with Ruff
  clean. Document Playwright passes 12/12 across desktop, tablet and mobile, including advisory
  brainstorm followed by routed chat edit, Reject and Accept.
