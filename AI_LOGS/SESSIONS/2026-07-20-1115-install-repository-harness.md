# Session Log

## Context

- User request: Install `hoangnb24/repository-harness` into this repository and `/home/linh/smart-exam-ai`, then provide usage guidance.
- Agent: Codex
- Date/time: 2026-07-20 11:15 +07

## Work Done

- Files changed: added the Repository Harness `docs/` and `scripts/` payload; appended the marked Harness block to `AGENTS.md`; appended Harness ignore rules to `.gitignore`; updated `AI_LOGS/HANDOFF.md` and `AI_LOGS/TASKS.md`; created this session log.
- Behavior changed: agents now enter through the existing project instructions plus the Harness request-class gate; Harness CLI `0.1.17` and its ignored SQLite durable layer are available locally.
- Commands run: installer dry-run and merge install, `scripts/bootstrap-harness.sh`, `harness-cli query matrix`, `harness-cli intake`, `harness-cli query contract`, `harness-cli audit`, `harness-cli query intakes`, and Git ignore/marker checks.

## Reasoning / Decisions

- Decision: use `--merge --refresh-agent-shim` rather than override mode.
- Reason: the repository already contained custom `AGENTS.md`, `README.md`, `Docs/`, and extensive uncommitted work that must be preserved.
- Alternatives considered: override mode was rejected because it would replace protected paths; installing the earlier unrelated `harness` skill was rejected because this repository is a project-level harness, not a Codex `SKILL.md` package.

## Verification

- Tests/checks: CLI version and schema contract, checksum-verified installer output, repeat bootstrap, one complete Harness marker pair, backup presence, Git ignore rules, recorded intake, and drift audit.
- Result: CLI `0.1.17`, database schema `13` current, intake `#1`, audit entropy `0/100`, marker and backup checks passed.

## Next Agent Notes

- Continue from: read `AGENTS.md`, then follow the existing `AI_LOGS` startup protocol; bootstrap only for change requests.
- Watch out for: uppercase `Docs/` remains the product source of truth while lowercase `docs/` contains generic Harness operating material. Do not merge or overwrite these directories blindly.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`
