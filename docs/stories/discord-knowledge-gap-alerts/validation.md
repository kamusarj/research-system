# Validation

## Proof Strategy

Prove that the gateway asks for guarded auto-approval, the backend refreshes gap state
after approval, scoped receipt reads expose only related active gaps, and bilingual
gateway output reports them. Existing service-account confinement and partial-source
behavior must remain green.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Discord payload auto-approval flag; bounded bilingual gap summary |
| Integration | Approved receipt item returns related active gap; unrelated/dismissed gaps stay absent; service account remains receipt-scoped |
| E2E | Deterministic gateway receipt response renders the alert in the channel summary |
| Platform | Compose config validates and gateway image builds without credentials |
| Performance | Gap summary query is bounded to one linked research item's tags |
| Logs/Audit | Existing secret/URL omission tests remain green |

## Fixtures

- One approved research item with one low-coverage tag.
- One related active gap, one unrelated active gap, and one dismissed related gap.
- One Discord receipt response containing a related gap summary.

## Commands

```text
apps/api/.venv/bin/python -m pytest apps/api/tests/test_intake_receipts.py apps/api/tests/test_ingestion.py apps/api/tests/test_link_to_hierarchy.py apps/api/tests/test_gaps.py
PYTHONPATH=apps/discord-bot apps/api/.venv/bin/python -m pytest apps/discord-bot/tests
cd apps/api && .venv/bin/ruff check app tests
docker compose config -q
```

## Acceptance Evidence

- Story proof: 45 backend tests and 36 gateway tests passed.
- Full regression: 252 backend, 36 gateway and 67 frontend tests passed.
- Full lint: backend Ruff, gateway Ruff and frontend ESLint passed.
- `docker compose config -q` passed.
- `docker compose --profile discord build discord-bot` built
  `businessaiagents-discord-bot:latest`.
- Real Discord delivery remains an owner-operated platform check because no bot token or
  allowlisted guild/channel was supplied.
