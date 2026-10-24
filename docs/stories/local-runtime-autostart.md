# US-LOCAL-RUNTIME-AUTOSTART Auto-start the local Research System runtime

## Status

implemented

## Lane

normal

## Product Contract

The four core local services start automatically from the Desktop repository after the owner's
desktop session begins and recover after Docker daemon restarts. The runtime keeps the conflict-free
frontend `13000` and API `18000` bindings and does not alter or restart the Smart Exam stack on port
`8080`.

## Relevant Product Docs

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`

## Acceptance Criteria

- Database, API, worker and frontend use Docker's `unless-stopped` restart policy.
- A user-level systemd service starts only the four core Compose services from
  `$HOME/Desktop/Business AI Agents` with `--no-build`.
- The service is enabled for the owner's user session and remains retryable while Docker is
  temporarily unavailable.
- API, worker and frontend bind mounts resolve to the current Desktop repository, never the retired
  `/run/media/linh/Data` path.
- API health succeeds directly on `18000`, through the frontend proxy on `13000`, and the frontend
  root returns HTTP 200.
- Existing Smart Exam containers and port `8080` are not recreated, stopped or reconfigured.

## Design Notes

- Commands: `scripts/start_local_autostart.sh`, `scripts/verify_local_autostart.sh`.
- Platform: systemd user unit installed from `ops/systemd/user/business-ai-agents.service`.
- Source: `$HOME/Desktop/Business AI Agents`, overrideable with `BUSINESS_AI_REPO_DIR`.
- Compose identity: explicit `businessaiagents` project name preserves the existing named volumes
  and container identity across repository moves.
- Ports: frontend `13000`, API `18000`; container ports stay unchanged.
- Data: existing PostgreSQL and document-object named volumes are preserved.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Not applicable; no application/domain code changes. |
| Integration | Compose config resolves all four restart policies and conflict-free ports. |
| E2E | Direct/proxied health plus frontend root return success. |
| Platform | User service enabled/active; live containers carry `unless-stopped` and bind the Desktop source. |
| Release | Smart Exam 8080 containers remain running with their original IDs. |

## Harness Delta

No Harness policy change. Original intake #73 records the initial setup; Desktop Harness intake #1
records the repository-move repair.

## Evidence

- `scripts/verify_local_autostart.sh`: pass from Desktop; Compose, installed launcher/unit, systemd
  state, live restart policies, Desktop bind sources, direct/proxied API health and frontend root
  all verified.
- The interrupted filesystem move was repaired with an ignore-existing merge: 193 missing
  application files and 842 repository/support files were added from `Data1`, zero existing Desktop
  files were overwritten, and the follow-up dry run reports zero missing repository files under the
  bounded exclusions.
- The first corrected start preserved PostgreSQL and named volumes while recreating only API,
  worker and frontend with Desktop bind sources. A second service restart was idempotent and
  preserved every Business AI Agents and Smart Exam container ID.
- Readiness is `ready` with a valid 45-node/32-edge graph, migration is `2d4e6f8a0b13 (head)`, and
  `/`, `/graph`, `/graph/system`, ports `13000`, `18000`, and untouched Smart Exam `8080` pass.
- Desktop Harness completion reran the verifier successfully; detailed trace #1 meets 3/3 and the
  drift audit reports zero unverified work and entropy 0/100.
