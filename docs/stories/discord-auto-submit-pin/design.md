# Design

## Domain Model

- Automatic intake: an ordinary allowlisted message with at least one supported URL/PDF.
- Pin request: one unsigned Discord snowflake supplied as text.
- Authorization: allowlisted guild/channel plus caller and app `PIN_MESSAGES` permissions.
- Target: one message fetched only through the interaction's current channel.

## Application Flow

1. `/pin` receives `message_id`.
2. Reject outside the existing allowlist.
3. Parse an unsigned 64-bit snowflake before any fetch.
4. Reject when caller lacks `PIN_MESSAGES`.
5. Reject when the bot/app lacks `PIN_MESSAGES`.
6. Defer an ephemeral response.
7. Fetch by ID through the current channel only.
8. Return success without mutation if already pinned.
9. Pin with a bounded audit reason naming the requesting Discord user ID.
10. Map Discord NotFound/Forbidden/HTTP failures to safe bilingual outcomes.

## Interface Contract

- Existing ordinary-message intake remains automatic.
- `/submit` remains optional compatibility.
- New `/pin message_id:<id>` returns only an ephemeral response.
- Success: pinned or already pinned.
- Refusals: invalid ID, caller permission missing, bot permission missing, message not found,
  Discord refused, or generic pin failure.

## Data Model

No local schema, storage or retention change. Discord owns pinned state and its audit log.

## UI / Platform Impact

- Installer requests `Pin Messages` in addition to existing channel permissions.
- User roles invoking `/pin` also need `Pin Messages`.
- `discord.py>=2.7.1,<3` is required for the current granular permission flag.

## Observability

- Success and typed failure log only bounded action names and exception type.
- Raw message content and token values are never logged.
- Discord receives a bounded pin audit reason with the requesting actor ID.

## Alternatives Considered

1. Require `Manage Messages`. Rejected because Discord requires the separate
   `PIN_MESSAGES` permission after 2026-02-23.
2. Let any allowlisted user pin. Rejected because allowlisting is an intake boundary, not
   moderation authority.
3. Search all allowlisted channels for the ID. Rejected because it broadens disclosure and
   mutation scope.
4. Automatically pin every submitted source. Rejected because the owner requested
   command-triggered pinning.
