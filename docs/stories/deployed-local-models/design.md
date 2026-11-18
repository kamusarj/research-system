# Design

## Boundaries / Flow

Static operator endpoint → bounded HTTP transport → local provider JSON protocol → existing graph
tool whitelist/executor → draft review. Model inventory and verify take only provider/model, no URL.
Use Ollama `/api/tags` + `/api/chat` or OpenAI-compatible `/v1/models` + `/v1/chat/completions`.
Structured tool envelope supports local models without native function-call extensions; malformed
output, unknown tools, non-object arguments and missing model fail closed.

## Interface / Data Model

POST `/chat/connections/local/models` `{provider}` → `{provider,models}`.
POST `/chat/connections/local/verify` `{provider,model_name}` → `{provider,model_name,verified:true}`.
System local create/import may provide installed model_name. Existing session model_name stores it;
send uses that exact model. No schema migration, durable connection table or personal key in browser.

## Platform / Observability

Same-host loopback bridges or remote-PC reverse SSH/private network endpoints. Optional Compose
profiles; team bridge uses packaged image and no code volume. Headers/key stay server-side; no raw
upstream errors, prompt or endpoint in log/UI. Record normalized model/provider usage as before.

## Alternatives

- Browser direct localhost: HTTPS/private-network/browser portability issues; use backend network path.
- Arbitrary URL per user: adds SSRF and credential management; use deployment configuration.
- Download-on-demand: not requested, disk insufficient; inventory reflects actual operator installation.
