# Session Log

## Context

- User request: Configure this project to start automatically whenever the machine starts, like the
  project on port `8080`.
- Agent: Codex
- Date/time: 2026-08-14 09:17 +07

## Work Done

- Files changed:
  - `docker-compose.yml`
  - `scripts/start_local_autostart.sh`
  - `scripts/verify_local_autostart.sh`
  - `ops/systemd/user/business-ai-agents.service`
  - `README.md`
  - `Docs/Graph Intelligence v2 Operations Runbook.md`
  - `docs/stories/local-runtime-autostart.md`
  - `.env` (local ignored port/CORS values only)
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - this session log
- Installed workstation files:
  - `~/.local/bin/business-ai-agents-autostart`
  - `~/.config/systemd/user/business-ai-agents.service`
- Behavior changed:
  - Core Compose services now use `restart: unless-stopped`.
  - An enabled systemd user service mounts the NTFS data volume when necessary and runs the four
    core services with existing images on API `18000` / frontend `13000`.
  - The separate Smart Exam Compose project on port `8080` is outside the service's scope.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake #73 and story `US-LOCAL-RUNTIME-AUTOSTART` add/update/complete commands
  - `systemctl --user daemon-reload`
  - `systemctl --user enable --now business-ai-agents.service`
  - `systemctl --user restart business-ai-agents.service`
  - `scripts/verify_local_autostart.sh`
  - Docker/systemd/HTTP readiness and unchanged-container inspections

## Reasoning / Decisions

- Decision: Combine Docker `unless-stopped` with a systemd user service instead of relying only on
  Docker daemon startup.
- Reason: Smart Exam's image/volume-only containers can restart directly at Docker boot, while this
  development Compose stack bind-mounts source from a desktop-managed NTFS volume under
  `/run/media`; that path may not exist when the Docker daemon starts.
- Alternatives considered:
  - Docker restart policy alone was rejected as insufficient for mount ordering.
  - A boot-time `/etc/fstab` plus root system service was not used because it requires administrator
    authorization and creates a broader boot configuration risk.

## Verification

- Tests/checks:
  - Compose config resolves `restart: unless-stopped` for database/API/worker/frontend and ports
    `18000`/`13000`.
  - Installed user service is enabled and active.
  - Live container restart policies are all `unless-stopped`.
  - API direct health and readiness pass; proxied health passes; frontend root returns HTTP 200.
  - Readiness reports 45 valid graph nodes and 32 valid edges.
  - Re-running the user service preserves all four core container IDs.
  - Smart Exam container IDs and port `8080` remain unchanged.
  - Harness story completion reruns `scripts/verify_local_autostart.sh` successfully.
- Result: Passed. Runtime is live and the autostart unit is installed/enabled.

## Next Agent Notes

- Continue from: The core stack is running on frontend `13000` and API `18000`.
- Watch out for: The service starts with the user's desktop session because the source volume is
  desktop-mounted; it is not a pre-login/headless boot service. A true cold reboot was not performed
  during this session.
- Suggested next command: After the next normal reboot/login, run
  `scripts/verify_local_autostart.sh` to record cold-boot proof.
