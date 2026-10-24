"""Pin requests validate IDs and keep user-facing outcomes bounded."""

import pytest

from app.guidance import pin_option_description, pin_result
from app.pinning import MAX_DISCORD_SNOWFLAKE, parse_message_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("123456789012345678", 123456789012345678),
        (" 42 ", 42),
        ("", None),
        ("0", None),
        ("-1", None),
        ("１２３", None),
        ("abc", None),
        (str(MAX_DISCORD_SNOWFLAKE), MAX_DISCORD_SNOWFLAKE),
        (str(MAX_DISCORD_SNOWFLAKE + 1), None),
    ],
)
def test_message_id_is_an_unsigned_ascii_discord_snowflake(value, expected):
    assert parse_message_id(value) == expected


def test_pin_copy_has_vietnamese_permission_and_outcome_messages():
    assert "Ghim tin nhắn" in pin_result("caller_forbidden", "vi")
    assert "Ghim tin nhắn" in pin_result("bot_forbidden", "en")
    assert "Đã ghim" in pin_result("pinned", "vi")
    assert "đã được ghim" in pin_result("already_pinned", "en")
    assert pin_result("not_found", "unsupported") == pin_result("not_found", "en")


def test_pin_option_description_falls_back_and_fits_discord():
    assert pin_option_description("unsupported") == pin_option_description("en")
    assert len(pin_option_description("vi")) <= 100
