# 0055 Deployed local model connections

Date: 2026-11-18

## Status

Accepted — user explicitly requests plan+implementation and both topologies/protocols.

## Decision

Add Ollama and OpenAI-compatible local chat/JSON adapters using fixed operator endpoints and optional
server-only keys. User selects/probes a listed model, pinned in the existing session. Deploy via narrow
host bridge or private endpoint/reverse SSH from a personal machine; browser calls only application API.
Keep existing tools/review/auth boundaries. No automatic model downloads, remote credentials or fallback.

## Consequences

Local means where model runs, not the browser's localhost. Remote PC must stay reachable; an offline
model fails visibly. Embedding configuration remains separate. Operator supplies endpoint, installed
model and any private network/SSH access. Plan and validation are under deployed-local-models.

## Sources

[Ollama chat](https://docs.ollama.com/api/chat), [inventory](https://docs.ollama.com/api/tags),
[Ollama networking](https://docs.ollama.com/faq),
[LM Studio compatibility](https://lmstudio.ai/docs/developer/openai-compat).
