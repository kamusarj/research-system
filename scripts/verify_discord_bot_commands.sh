#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

docker compose --profile discord build discord-bot
DISCORD_IMAGE_REF="$(
  docker compose --profile discord config --format json |
    python3 -c '
import json
import sys

config = json.load(sys.stdin)
service = config["services"]["discord-bot"]
print(service.get("image") or "{}-discord-bot".format(config["name"]))
'
)"
docker image inspect "${DISCORD_IMAGE_REF}" >/dev/null

# The smoke runs inside the production image, where discord.py is installed. It creates no
# network connection and injects no real token or repository environment.
docker run --rm -i --entrypoint python "${DISCORD_IMAGE_REF}" - <<'PY'
import asyncio
from types import SimpleNamespace

import discord

from app.bot import IntakeGatewayClient
from app.config import BotConfig

assert (discord.version_info.major, discord.version_info.minor, discord.version_info.micro) >= (
    2,
    7,
    1,
)
assert "pin_messages" in discord.Permissions.VALID_FLAGS
expected = {"help", "guide", "sources", "ping", "pin", "submit", "status"}
config = BotConfig(
    discord_token="smoke-not-a-secret",
    api_base_url="http://api.invalid",
    api_token="smoke-not-a-secret",
    namespace="discord",
    guild_ids=frozenset({"123"}),
    channel_ids=frozenset({"456"}),
    provider=None,
    auto_approve_links=True,
    locale="vi",
    poll_interval_seconds=0.01,
    poll_attempts=1,
    request_timeout_seconds=1,
    per_user_messages_per_minute=10,
)
client = IntakeGatewayClient(config)

global_commands = {command.name for command in client.tree.get_commands()}
assert global_commands == expected, (global_commands, expected)

guild = discord.Object(id=123)
client.tree.copy_global_to(guild=guild)
guild_commands = {command.name for command in client.tree.get_commands(guild=guild)}
assert guild_commands == expected, (guild_commands, expected)


class MessageSink:
    def __init__(self):
        self.messages = []

    async def send_message(self, content, *, ephemeral=False):
        self.messages.append((content, ephemeral))

    async def send(self, content, *, ephemeral=False):
        self.messages.append((content, ephemeral))


class FakeResponse(MessageSink):
    def __init__(self):
        super().__init__()
        self.deferred = False

    async def defer(self, *, ephemeral=False):
        self.deferred = True
        self.ephemeral = ephemeral


class FakeMessage:
    def __init__(self, *, pinned=False):
        self.channel = SimpleNamespace(id=456)
        self.pinned = pinned
        self.pin_reasons = []

    async def pin(self, *, reason=None):
        self.pin_reasons.append(reason)
        self.pinned = True


class FakeChannel:
    def __init__(self, target):
        self.target = target
        self.fetches = []

    async def fetch_message(self, message_id):
        self.fetches.append(message_id)
        return self.target


class FakeInteraction:
    def __init__(
        self,
        *,
        caller_can_pin=True,
        bot_can_pin=True,
        target=None,
        guild_id=123,
    ):
        self.guild_id = guild_id
        self.channel_id = 456
        self.user = SimpleNamespace(id=999)
        self.permissions = SimpleNamespace(pin_messages=caller_can_pin)
        self.app_permissions = SimpleNamespace(pin_messages=bot_can_pin)
        self.channel = FakeChannel(target or FakeMessage())
        self.response = FakeResponse()
        self.followup = MessageSink()


async def verify_pin_authorization():
    pin_command = client.tree.get_command("pin")
    assert pin_command is not None

    invalid = FakeInteraction()
    await pin_command.callback(invalid, "not-a-message-id")
    assert invalid.channel.fetches == []
    assert invalid.response.messages[0][1] is True

    outside_allowlist = FakeInteraction(guild_id=999)
    await pin_command.callback(outside_allowlist, "789")
    assert outside_allowlist.channel.fetches == []

    caller_denied = FakeInteraction(caller_can_pin=False)
    await pin_command.callback(caller_denied, "789")
    assert caller_denied.channel.fetches == []
    assert "Pin Messages" in caller_denied.response.messages[0][0]

    bot_denied = FakeInteraction(bot_can_pin=False)
    await pin_command.callback(bot_denied, "789")
    assert bot_denied.channel.fetches == []
    assert "Pin Messages" in bot_denied.response.messages[0][0]

    already_target = FakeMessage(pinned=True)
    already = FakeInteraction(target=already_target)
    await pin_command.callback(already, "789")
    assert already.channel.fetches == [789]
    assert already_target.pin_reasons == []
    assert already.response.deferred and already.response.ephemeral

    target = FakeMessage()
    allowed = FakeInteraction(target=target)
    await pin_command.callback(allowed, "789")
    assert allowed.channel.fetches == [789]
    assert len(target.pin_reasons) == 1
    assert "999" in target.pin_reasons[0]
    assert len(target.pin_reasons[0]) <= 512
    assert allowed.followup.messages[0][1] is True


async def verify_automatic_message_intake():
    collected = []
    original_collect = client._collect

    async def capture(message, incoming, plan):
        collected.append((message, incoming, plan))

    client._collect = capture
    try:
        message = SimpleNamespace(
            id=111,
            channel=SimpleNamespace(id=456),
            guild=SimpleNamespace(id=123),
            author=SimpleNamespace(id=999, bot=False),
            content="Read https://example.com/public-article",
            attachments=(),
            mentions=(),
        )
        await client.on_message(message)
    finally:
        client._collect = original_collect

    assert len(collected) == 1
    assert collected[0][2].urls == ["https://example.com/public-article"]


async def main():
    await verify_automatic_message_intake()
    await verify_pin_authorization()
    await client.api.aclose()


asyncio.run(main())
print(
    "Discord command smoke: automatic plain-link intake passed; 7/7 commands registered; "
    "pin allowlist, permissions, idempotency and success paths passed."
)
PY
