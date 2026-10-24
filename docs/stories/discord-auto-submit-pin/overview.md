# Discord Automatic Intake and Authorized Pin Command

## Current Behavior

An allowlisted ordinary Discord message containing public links or supported PDFs is
already submitted automatically. The `/submit` compatibility command can make the help
surface look as though it is required. The bot cannot pin a selected Discord message.

## Target Behavior

Automatic message intake is explicitly the primary path: posting a link is sufficient and
`/submit` is optional. An allowlisted user with Discord's current `PIN_MESSAGES` permission
can run `/pin message_id:<id>` to pin a message from that same channel. The bot also checks
its resolved `PIN_MESSAGES` permission, never searches another channel, treats an already
pinned message idempotently and returns bounded ephemeral outcomes.

## Affected Users

- Researchers posting sources in allowlisted channels.
- Channel moderators/users explicitly granted Pin Messages.
- Discord administrators installing the bot.

## Affected Product Docs

- `apps/discord-bot/README.md`
- `Docs/Discord Bot Test Runbook.md`
- `Docs/Research System Completion Plan.md`
- `docs/decisions/0018-discord-pin-authorization.md`

## Non-Goals

- No `/unpin`.
- No cross-channel or cross-guild message lookup.
- No automatic pin after every intake.
- No Research API, service-account scope, database or graph-governance change.
- No replacement of Discord's native audit log with a local shadow log.
