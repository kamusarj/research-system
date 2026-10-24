# US-DOCUMENT-LIST-OPEN-EDITOR Open Uploaded Document Editor

## Status

implemented

## Lane

normal

## Product Contract

In the uploaded-document list, selecting a document by its filename must open that document's detail workspace. When the processed document is editable, the destination must expose its editor rather than requiring users to discover an analysis-only action.

## Relevant Product Docs

- `docs/stories/document-uploaded-editing/design.md`
- `docs/stories/document-uploaded-editing/validation.md`
- `docs/decisions/0039-loss-safe-binary-document-editing.md`

## Acceptance Criteria

- Every uploaded filename is a keyboard-accessible link to `/documents/{workspace_id}`.
- The primary row action uses an open-document label and reaches the same workspace.
- Opening a processed editable PDF/DOCX from the list renders the extracted-text editor while preserving original-file access.
- Download and Research links remain separate actions.

## Design Notes

- UI surface: `apps/web/app/documents/page.tsx`.
- Destination remains the existing `apps/web/app/documents/[id]/page.tsx` route.
- No API, persistence or document-representation change is required.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Translation and type checks cover the new label through the existing frontend suite. |
| Integration | List API data maps its workspace ID to the detail route. |
| E2E | Clicking an uploaded filename navigates to the detail route and displays the editable document content. |
| Platform | Live route responds on the current local runtime. |
| Release | No page-level horizontal overflow at supported viewports. |

## Harness Delta

This regression shows the existing binary-editing E2E entered the detail route directly and missed list-to-editor discoverability. Add a list-navigation browser case to the durable proof.

## Evidence

- Red proof: the initial desktop browser test could not find a filename link in the uploaded-document list.
- `npm test -- --run`: 121/121 passed; focused navigation/editor tests pass 11/11.
- `npm run lint` and `npx tsc --noEmit`: passed.
- Full `e2e/document-upload.spec.ts`: 24/24 passed across desktop, tablet and mobile Chrome.
- Live existing-DOCX proof: clicking `VLA_Survey_Report_Nguyen_Thi_Yen.docx` opened its real workspace, exposed a non-readonly 40,222-character editor and produced zero console errors.
- `scripts/bin/harness-cli story complete US-DOCUMENT-LIST-OPEN-EDITOR --json`: fresh proof passed.
- Harness trace #60 meets the normal-lane standard tier 2/3; owner correction is recorded as intervention #21.
