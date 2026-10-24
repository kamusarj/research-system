# Validation

## Proof Strategy

Use provider doubles to inspect the exact bounded/redacted instructions without sending document
content to a real provider during tests. Preserve all existing graph-governance tests.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Document context includes canonical text and truncation metadata. |
| Integration | Document-scoped turn sends redacted canonical text to the provider double. |
| E2E | Existing document-to-chat navigation remains available. |
| Platform | Rebuilt API/worker remain ready; no live provider call is required. |
| Performance | Inner document excerpt and final context both remain character-bounded. |
| Logs/Audit | Tests and inspection confirm content is not added to audit payloads. |

## Fixtures

- Local document workspace linked to a ResearchItem with deterministic text and a redaction marker.
- Sequenced graph-chat provider double.

## Commands

```text
cd apps/api
uv run ruff check app tests
uv run python -m pytest tests/test_graph_chat.py
uv run python -m pytest
```

## Acceptance Evidence

- Focused graph-chat proof: 10/10 tests pass, including canonical text inclusion, email redaction,
  inner document bound and existing governed proposal behavior.
- Full backend proof: Ruff passes and Pytest passes 257/257.
- Provider proof uses only a deterministic provider double; no user document was sent to a live
  provider during verification.
- API and worker images rebuilt; health is `ok`, readiness is `ready`, graph invariants remain
  valid at 45 nodes / 32 edges and fresh logs contain no application errors.
- No schema, retention, tool permission, approval or publication behavior changed.
