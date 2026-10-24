# 0018 Discord Pin Command Authorization

Date: 2026-07-30

## Status

Accepted

## Context

The owner clarified that ordinary link messages must enter intake automatically and asked
for a command that pins a selected Discord message. Pinning mutates externally managed
channel state. Discord split pinning from `MANAGE_MESSAGES`; since 2026-02-23 the operation
requires the granular `PIN_MESSAGES` permission.

## Decision

Ordinary allowlisted messages remain the primary zero-command intake path. `/submit` remains
an optional compatibility path and is labeled as such.

Add `/pin message_id:<id>`. It operates only in the interaction's current allowlisted
channel, parses the target as an unsigned 64-bit Discord snowflake, and requires resolved
`PIN_MESSAGES` permission for both caller and bot. It never searches another channel.
Already-pinned targets succeed without another mutation. The pin request includes a bounded
Discord audit-log reason; local logs exclude message content.

Pin support requires `discord.py>=2.7.1,<3`, which exposes the granular permission.

## Alternatives Considered

1. Use `MANAGE_MESSAGES`. Rejected because Discord's current endpoint requires
   `PIN_MESSAGES`.
2. Let every allowlisted researcher pin. Rejected because intake authorization does not
   imply channel moderation authority.
3. Add unpin or cross-channel lookup. Rejected as unnecessary privilege and blast radius.
4. Pin every automatically submitted link. Rejected because pinning is explicitly
   user-commanded.

## Consequences

Positive:

- Users submit links by posting them normally, with no required command.
- Authorized moderators can pin a chosen same-channel message without giving the Research
  API any new authority.
- Discord's permission system and audit log remain authoritative.

Tradeoffs:

- Installers must grant the bot `Pin Messages`.
- Callers without `Pin Messages` receive an ephemeral refusal.
- A message ID must be copied through Discord Developer Mode.
- Live mutation proof still requires an owner-controlled guild; repository proof uses the
  actual callback with a credential-free platform double.

## Follow-Up

- Run the live `/pin` acceptance case after the owner supplies a test bot token and guild.
- Add unpin only through a separately authorized story if product need appears.

## References

- <https://docs.discord.com/developers/resources/message#pin-message>
- <https://docs.discord.com/developers/topics/permissions>
- <https://docs.discord.com/developers/change-log>
