# Document Knowledge Graph Workspace

## Current Behavior

Document uploads are extracted, evaluated and automatically receive an isolated graph only when
their paper-fit score is at least 60. The document page already draws that graph, but the document
list no longer exposes a distinct `View analysis` entry. A selected node shows its provider summary
and evidence, but there is no independently generated AI research, explicit source-vs-AI comparison
or one-action research-to-change-set workflow.

The global relationship view pages through a bounded subset while hierarchy reads the separate
Business AI Agents ontology. Consequently the two views can show different corpora and hierarchy
does not necessarily reflect the relationships just added to the approved knowledge graph.

## Target Behavior

Every supported upload with readable canonical text automatically receives its own isolated graph,
independent of paper-fit routing. `View analysis` opens the graph directly. Selecting a child node
shows a bounded 150–200 character source-grounded summary, optional independent AI research and an
explicit consistency/difference comparison.

Researchers can ask AI to research selected or all semantic nodes. They can also run one governed
action that researches the graph and creates a draft knowledge-graph change set. AI never publishes
or deletes canonical knowledge directly; the existing validation, review, approve and apply flow
remains mandatory.

The relationship view loads the complete current corpus up to the explicit 1,000-node operational
safety ceiling instead of a hidden 100-item display cap. Its hierarchy view is derived from the same
approved relationship corpus. The canonical Business AI Agents ontology remains available through a
separate system-map route and API.

## Affected Users

- Researchers uploading, reviewing and promoting document knowledge.
- Owners reviewing and applying graph change sets.
- Viewers browsing relationship, hierarchy and the separate system map.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Research System Implementation Plan.md`
- `Docs/Research System Architecture Design.md`
- `docs/stories/editable-document-workspaces.md`
- `docs/decisions/0024-human-reviewed-document-ai-edit-and-auto-rag.md`

## Non-Goals

- Direct AI publication into the canonical knowledge graph.
- Autonomous web crawling or unverifiable citation generation.
- Removing all server-side graph resource bounds.
- Changing immutable document-source versioning or original PDF/DOCX preservation.

