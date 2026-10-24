"""Phần trợ giúp Discord luôn đầy đủ, dùng tiếng Việt và không vượt giới hạn."""

import pytest

from app.guidance import (
    COMMAND_DESCRIPTIONS,
    COMMAND_NAMES,
    command_description,
    guide_text,
    help_text,
    ping_text,
    sources_text,
)
from app.messages import NOTHING_TO_COLLECT

DISCORD_DESCRIPTION_LIMIT = 100
BOT_REPLY_LIMIT = 1800
EXPECTED_COMMANDS = {"help", "guide", "sources", "ping", "pin", "submit", "status"}


def test_command_catalog_is_complete_and_each_command_appears_in_help():
    assert set(COMMAND_NAMES) == EXPECTED_COMMANDS
    assert set(COMMAND_DESCRIPTIONS) == EXPECTED_COMMANDS

    for locale in ("vi", "en"):
        text = help_text(locale)
        for command in EXPECTED_COMMANDS:
            assert f"`/{command}" in text


@pytest.mark.parametrize("locale", ["vi", "en"])
def test_all_guidance_fits_in_one_discord_reply(locale):
    for text in (help_text(locale), guide_text(locale), sources_text(locale)):
        assert 0 < len(text) <= BOT_REPLY_LIMIT


def test_command_descriptions_fit_discord_and_always_use_vietnamese():
    for command in COMMAND_NAMES:
        assert len(command_description(command, "vi")) <= DISCORD_DESCRIPTION_LIMIT
        assert command_description(command, "unsupported") == command_description(command, "en")


def test_guidance_explains_sources_limits_graph_review_and_gaps():
    vietnamese = "\n".join((help_text("vi"), guide_text("vi"), sources_text("vi")))

    assert "20 liên kết" in vietnamese
    assert "5 tệp PDF" in vietnamese
    assert "20 MB" in vietnamese
    assert "đồ thị quan hệ" in vietnamese
    assert "khoảng trống tri thức" in vietnamese
    assert "bộ thay đổi phân cấp" in vietnamese
    assert "Reel" in vietnamese
    assert "Không cần dùng `/submit`" in vietnamese
    assert "Ghim tin nhắn" in vietnamese


def test_ping_handles_known_and_unknown_latency():
    assert "42 ms" in ping_text("vi", 42)
    assert "ms" not in ping_text("en", None)


def test_mention_without_a_source_points_to_help():
    assert "/help" in NOTHING_TO_COLLECT["vi"]
