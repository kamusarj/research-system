"""The Discord surface: listen, react, reply, and delegate everything else.

Nothing in this module decides what a source means. It recognises a message, asks the
Research API to take it, and reports back what the API said. That boundary is what keeps
the bot replaceable and the research rules in one place (DEC-028).
"""

from __future__ import annotations

import logging
import math
import time

import discord
import httpx

from app.api_client import ResearchAPIClient, ResearchAPIError
from app.config import BotConfig, load_config
from app.gateway import (
    OUTCOME_REACTIONS,
    Allowlist,
    Attachment,
    IncomingMessage,
    document_item_ref,
    plan_message,
    receipt_outcome,
    receipt_payload,
)
from app.guidance import (
    COMMAND_ERROR,
    PRESENCE_TEXT,
    command_description,
    guide_text,
    help_text,
    localized,
    pin_option_description,
    pin_result,
    ping_text,
    sources_text,
)
from app.messages import NOT_PERMITTED, NOTHING_TO_COLLECT, summarize_receipt
from app.pinning import parse_message_id
from app.rate_limit import PerUserRateLimit

logger = logging.getLogger("discord-gateway")

MAX_REPLY_CHARS = 1800


def to_incoming(message: discord.Message) -> IncomingMessage:
    return IncomingMessage(
        id=str(message.id),
        channel_id=str(message.channel.id),
        guild_id=str(message.guild.id) if message.guild else None,
        author_id=str(message.author.id),
        author_is_bot=bool(message.author.bot),
        content=message.content or "",
        attachments=tuple(
            Attachment(
                id=str(item.id),
                filename=item.filename,
                content_type=item.content_type,
                size=item.size,
                url=item.url,
            )
            for item in message.attachments
        ),
    )


class IntakeGatewayClient(discord.Client):
    def __init__(self, config: BotConfig) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        # Nội dung trả lời có thể chứa tiêu đề/nhãn lấy từ nguồn hoặc AI; không để chúng ping
        # @everyone, vai trò hay người dùng.
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.config = config
        self.allowlist = Allowlist(guild_ids=config.guild_ids, channel_ids=config.channel_ids)
        self.api = ResearchAPIClient(
            config.api_base_url, config.api_token, config.request_timeout_seconds
        )
        self.rate_limit = PerUserRateLimit(config.per_user_messages_per_minute)
        self.tree = discord.app_commands.CommandTree(self)
        self._register_commands()

    async def setup_hook(self) -> None:
        for guild_id in self.config.guild_ids:
            guild = discord.Object(id=int(guild_id))
            # Commands are defined globally in this process, then copied into each
            # allowlisted guild so they are available immediately during local testing.
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(
                "Discord application commands synced",
                extra={
                    "action": "gateway.commands.synced",
                    "guild_id": guild_id,
                    "command_count": len(synced),
                },
            )

    async def close(self) -> None:
        await self.api.aclose()
        await super().close()

    async def on_ready(self) -> None:
        try:
            await self.change_presence(
                activity=discord.Game(name=localized(PRESENCE_TEXT, self.config.locale))
            )
        except discord.DiscordException:
            logger.warning(
                "Discord presence could not be updated",
                extra={"action": "gateway.presence.failed"},
            )
        logger.info(
            "Discord gateway ready",
            extra={"action": "gateway.ready", "guild_count": len(self.config.guild_ids)},
        )

    async def on_message(self, message: discord.Message) -> None:
        incoming = to_incoming(message)
        if not self.allowlist.permits(incoming):
            return
        plan = plan_message(incoming)
        if not plan.actionable:
            if plan.skipped:
                await message.reply(
                    "\n".join(f"• {item}" for item in plan.skipped)[:MAX_REPLY_CHARS],
                    mention_author=False,
                )
            elif self.user in message.mentions:
                await message.reply(
                    NOTHING_TO_COLLECT.get(self.config.locale, NOTHING_TO_COLLECT["en"]),
                    mention_author=False,
                )
            return

        if not self.rate_limit.allow(incoming.author_id, time.monotonic()):
            await message.add_reaction("🚫")
            return

        await self._collect(message, incoming, plan)

    async def _collect(self, message: discord.Message, incoming, plan) -> None:
        await message.add_reaction(OUTCOME_REACTIONS["working"])
        try:
            receipt = await self.api.create_receipt(
                receipt_payload(
                    incoming,
                    plan,
                    namespace=self.config.namespace,
                    provider=self.config.provider,
                    auto_approve=self.config.auto_approve_links,
                )
            )
            for attachment in plan.documents:
                # Bytes are persisted through the API before any asynchronous processing
                # starts, so a Discord CDN link expiring cannot orphan the work.
                content = await self._download(attachment)
                if content is None:
                    plan.skipped.append(f"{attachment.filename}: không thể tải xuống")
                    continue
                receipt = await self.api.attach_document(
                    receipt["id"],
                    filename=attachment.filename,
                    content=content,
                    content_type=attachment.content_type or "application/pdf",
                    external_item_ref=document_item_ref(incoming, attachment),
                    provider=self.config.provider,
                )
            receipt = await self.api.await_receipt(
                receipt["id"],
                interval_seconds=self.config.poll_interval_seconds,
                attempts=self.config.poll_attempts,
            )
        except ResearchAPIError:
            await self._replace_reaction(message, OUTCOME_REACTIONS["failed"])
            await message.reply(localized(COMMAND_ERROR, self.config.locale), mention_author=False)
            return

        await self._replace_reaction(message, OUTCOME_REACTIONS[receipt_outcome(receipt)])
        summary = summarize_receipt(receipt, plan.skipped, self.config.locale)
        if summary:
            await message.reply(summary[:MAX_REPLY_CHARS], mention_author=False)

    async def _download(self, attachment: Attachment) -> bytes | None:
        """Pull the attachment bytes from Discord's CDN before handing them to the API."""

        try:
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.get(attachment.url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            logger.warning(
                "Attachment download failed",
                extra={
                    "action": "attachment.download.failed",
                    "exception_type": type(exc).__qualname__,
                },
            )
            return None

    async def _replace_reaction(self, message: discord.Message, reaction: str) -> None:
        try:
            await message.remove_reaction(OUTCOME_REACTIONS["working"], self.user)
        except discord.DiscordException:
            pass
        try:
            await message.add_reaction(reaction)
        except discord.DiscordException:
            pass

    def _register_commands(self) -> None:
        config = self.config
        api = self.api
        allowlist = self.allowlist

        def permitted(interaction: discord.Interaction) -> bool:
            guild_id = str(interaction.guild_id) if interaction.guild_id else None
            channel_id = str(interaction.channel_id) if interaction.channel_id else None
            return bool(guild_id in allowlist.guild_ids and channel_id in allowlist.channel_ids)

        async def reject_unpermitted(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                NOT_PERMITTED.get(config.locale, NOT_PERMITTED["en"]), ephemeral=True
            )

        @self.tree.command(name="help", description=command_description("help", config.locale))
        async def help_command(interaction: discord.Interaction) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            await interaction.response.send_message(
                help_text(config.locale)[:MAX_REPLY_CHARS], ephemeral=True
            )

        @self.tree.command(name="guide", description=command_description("guide", config.locale))
        async def guide(interaction: discord.Interaction) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            await interaction.response.send_message(
                guide_text(config.locale)[:MAX_REPLY_CHARS], ephemeral=True
            )

        @self.tree.command(
            name="sources", description=command_description("sources", config.locale)
        )
        async def sources(interaction: discord.Interaction) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            await interaction.response.send_message(
                sources_text(config.locale)[:MAX_REPLY_CHARS], ephemeral=True
            )

        @self.tree.command(name="ping", description=command_description("ping", config.locale))
        async def ping(interaction: discord.Interaction) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            latency = self.latency
            latency_ms = (
                max(0, round(latency * 1000)) if math.isfinite(latency) and latency >= 0 else None
            )
            await interaction.response.send_message(
                ping_text(config.locale, latency_ms), ephemeral=True
            )

        @self.tree.command(name="pin", description=command_description("pin", config.locale))
        @discord.app_commands.describe(message_id=pin_option_description(config.locale))
        async def pin(interaction: discord.Interaction, message_id: str) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            parsed_id = parse_message_id(message_id)
            if parsed_id is None:
                await interaction.response.send_message(
                    pin_result("invalid_id", config.locale), ephemeral=True
                )
                return
            if not interaction.permissions.pin_messages:
                await interaction.response.send_message(
                    pin_result("caller_forbidden", config.locale), ephemeral=True
                )
                return
            if not interaction.app_permissions.pin_messages:
                await interaction.response.send_message(
                    pin_result("bot_forbidden", config.locale), ephemeral=True
                )
                return
            channel = interaction.channel
            if channel is None or not hasattr(channel, "fetch_message"):
                await interaction.response.send_message(
                    pin_result("not_found", config.locale), ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)
            try:
                target = await channel.fetch_message(parsed_id)
                if str(target.channel.id) != str(interaction.channel_id):
                    await interaction.followup.send(
                        pin_result("not_found", config.locale), ephemeral=True
                    )
                    return
                if target.pinned:
                    await interaction.followup.send(
                        pin_result("already_pinned", config.locale), ephemeral=True
                    )
                    return
                await target.pin(
                    reason=f"Requested through /pin by Discord user {interaction.user.id}"
                )
            except discord.NotFound:
                await interaction.followup.send(
                    pin_result("not_found", config.locale), ephemeral=True
                )
                return
            except discord.Forbidden as exc:
                logger.warning(
                    "Discord message pin was forbidden",
                    extra={
                        "action": "gateway.pin.forbidden",
                        "exception_type": type(exc).__qualname__,
                    },
                )
                await interaction.followup.send(
                    pin_result("bot_forbidden", config.locale), ephemeral=True
                )
                return
            except discord.HTTPException as exc:
                logger.warning(
                    "Discord message pin failed",
                    extra={
                        "action": "gateway.pin.failed",
                        "exception_type": type(exc).__qualname__,
                    },
                )
                await interaction.followup.send(pin_result("failed", config.locale), ephemeral=True)
                return
            logger.info(
                "Discord message pinned",
                extra={"action": "gateway.pin.completed", "guild_id": str(interaction.guild_id)},
            )
            await interaction.followup.send(pin_result("pinned", config.locale), ephemeral=True)

        @self.tree.command(name="status", description=command_description("status", config.locale))
        async def status(interaction: discord.Interaction, message_id: str) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                # A person has the Discord message ID in front of them, not the receipt ID,
                # so the lookup goes through the occurrence reference the receipt recorded.
                receipt = await api.find_receipt(message_id)
            except ResearchAPIError as failure:
                await interaction.followup.send(str(failure), ephemeral=True)
                return
            await interaction.followup.send(
                summarize_receipt(receipt, [], config.locale)[:MAX_REPLY_CHARS] or "—",
                ephemeral=True,
            )

        @self.tree.command(name="submit", description=command_description("submit", config.locale))
        async def submit(interaction: discord.Interaction, url: str) -> None:
            if not permitted(interaction):
                await reject_unpermitted(interaction)
                return
            await interaction.response.defer()
            incoming = IncomingMessage(
                id=str(interaction.id),
                channel_id=str(interaction.channel_id),
                guild_id=str(interaction.guild_id),
                author_id=str(interaction.user.id),
                author_is_bot=False,
                content=url,
            )
            plan = plan_message(incoming)
            if not plan.actionable:
                await interaction.followup.send(
                    NOTHING_TO_COLLECT.get(config.locale, NOTHING_TO_COLLECT["en"])
                )
                return
            try:
                receipt = await api.create_receipt(
                    receipt_payload(
                        incoming,
                        plan,
                        namespace=config.namespace,
                        provider=config.provider,
                        auto_approve=config.auto_approve_links,
                    )
                )
                receipt = await api.await_receipt(
                    receipt["id"],
                    interval_seconds=config.poll_interval_seconds,
                    attempts=config.poll_attempts,
                )
            except ResearchAPIError as failure:
                await interaction.followup.send(str(failure))
                return
            await interaction.followup.send(
                summarize_receipt(receipt, plan.skipped, config.locale)[:MAX_REPLY_CHARS] or "—"
            )

        @self.tree.error
        async def command_error(
            interaction: discord.Interaction, error: discord.app_commands.AppCommandError
        ) -> None:
            logger.warning(
                "Discord application command failed",
                extra={
                    "action": "gateway.command.failed",
                    "exception_type": type(error).__qualname__,
                },
            )
            message = localized(COMMAND_ERROR, config.locale)
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    config = load_config()
    if not config.configured:
        # Refusing to start is safer than running with an empty allowlist, which would
        # accept intake from any server the bot happens to be in.
        raise SystemExit(
            "Cổng Discord chưa được cấu hình. Còn thiếu: " + ", ".join(config.missing())
        )
    client = IntakeGatewayClient(config)
    client.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
