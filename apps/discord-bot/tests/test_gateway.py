"""What the gateway decides, tested without Discord or a network.

Everything that matters about this bot is a decision: is this channel allowed, what does
this message carry, what should the API be asked for, and what should the channel be told.
Those are all here, so the Discord glue stays thin enough to read.
"""

import pytest

from app.gateway import (
    Allowlist,
    Attachment,
    IncomingMessage,
    document_item_ref,
    extract_urls,
    item_outcome,
    plan_message,
    receipt_outcome,
    receipt_payload,
    receipt_settled,
)
from app.messages import describe_error, summarize_receipt
from app.rate_limit import PerUserRateLimit


def message(**overrides) -> IncomingMessage:
    fields = {
        "id": "1234567890",
        "channel_id": "channel-1",
        "guild_id": "guild-1",
        "author_id": "user-1",
        "author_is_bot": False,
        "content": "",
        "attachments": (),
    }
    fields.update(overrides)
    return IncomingMessage(**fields)


def pdf(**overrides) -> Attachment:
    fields = {
        "id": "attach-1",
        "filename": "paper.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "url": "https://cdn.discord.example/paper.pdf",
    }
    fields.update(overrides)
    return Attachment(**fields)


class TestAllowlist:
    def test_an_unlisted_channel_is_refused(self):
        allowlist = Allowlist(frozenset({"guild-1"}), frozenset({"channel-1"}))

        assert allowlist.permits(message()) is True
        assert allowlist.permits(message(channel_id="channel-2")) is False
        assert allowlist.permits(message(guild_id="guild-2")) is False

    def test_an_empty_allowlist_permits_nothing(self):
        # A gateway that defaults to open would collect from any server it is invited to.
        assert Allowlist().permits(message()) is False

    def test_direct_messages_are_refused(self):
        allowlist = Allowlist(frozenset({"guild-1"}), frozenset({"channel-1"}))

        assert allowlist.permits(message(guild_id=None)) is False

    def test_the_bot_does_not_answer_itself(self):
        allowlist = Allowlist(frozenset({"guild-1"}), frozenset({"channel-1"}))

        assert allowlist.permits(message(author_is_bot=True)) is False


class TestUrlExtraction:
    def test_every_link_in_a_message_is_collected(self):
        urls = extract_urls("Look at https://example.com/a and https://example.com/b for context")

        assert urls == ["https://example.com/a", "https://example.com/b"]

    def test_trailing_punctuation_is_not_part_of_the_link(self):
        assert extract_urls("see https://example.com/report.") == ["https://example.com/report"]
        assert extract_urls("(https://example.com/a)") == ["https://example.com/a"]

    def test_the_same_link_twice_is_collected_once(self):
        assert extract_urls("https://example.com/a https://EXAMPLE.com/a") == [
            "https://example.com/a"
        ]

    def test_a_message_with_no_link_yields_nothing(self):
        assert extract_urls("just talking about research") == []


class TestMessagePlan:
    def test_a_plain_link_message_is_actionable_without_a_submit_command(self):
        plan = plan_message(message(content="Please read https://example.com/article"))

        assert plan.actionable is True
        assert plan.urls == ["https://example.com/article"]

    def test_links_and_pdfs_are_both_collected(self):
        plan = plan_message(message(content="https://example.com/paper", attachments=(pdf(),)))

        assert plan.urls == ["https://example.com/paper"]
        assert [item.filename for item in plan.documents] == ["paper.pdf"]
        assert plan.actionable is True

    def test_a_non_pdf_attachment_is_refused_and_said_so(self):
        plan = plan_message(
            message(attachments=(pdf(filename="notes.docx", content_type="application/msword"),))
        )

        assert plan.documents == []
        assert "chỉ thu thập tệp PDF" in plan.skipped[0]

    def test_an_oversized_attachment_is_refused_and_said_so(self):
        plan = plan_message(message(attachments=(pdf(size=25_000_000),)))

        assert plan.documents == []
        assert "vượt giới hạn 20 MB" in plan.skipped[0]

    def test_a_pdf_without_a_declared_type_is_recognised_by_its_name(self):
        plan = plan_message(message(attachments=(pdf(content_type=None),)))

        assert [item.filename for item in plan.documents] == ["paper.pdf"]

    def test_a_flood_of_links_is_bounded_and_reported(self):
        content = " ".join(f"https://example.com/{index}" for index in range(30))

        plan = plan_message(message(content=content))

        assert len(plan.urls) == 20
        # Silently dropping ten sources would look identical to collecting them.
        assert "chỉ nhận 20 liên kết đầu tiên trong tổng số 30 liên kết" in plan.skipped


class TestReceiptPayload:
    def test_the_message_id_is_what_makes_a_replay_idempotent(self):
        incoming = message(content="https://example.com/a")
        payload = receipt_payload(incoming, plan_message(incoming), namespace="discord")

        assert payload["source"]["type"] == "discord"
        assert payload["source"]["occurrence_ref"] == incoming.id
        assert payload["source"]["container_ref"] == incoming.channel_id
        assert payload["source"]["external_actor_ref"] == incoming.author_id
        assert payload["items"] == [
            {
                "kind": "url",
                "url": "https://example.com/a",
                "auto_approve": True,
            }
        ]

    def test_a_provider_is_only_sent_when_one_is_configured(self):
        incoming = message(content="https://example.com/a")
        plan = plan_message(incoming)

        with_provider = receipt_payload(incoming, plan, namespace="d", provider="deepseek")
        without = receipt_payload(incoming, plan, namespace="d")

        assert with_provider["items"][0]["provider"] == "deepseek"
        assert "provider" not in without["items"][0]

    def test_guarded_auto_approval_can_be_disabled_by_deployment(self):
        incoming = message(content="https://example.com/a")

        payload = receipt_payload(
            incoming,
            plan_message(incoming),
            namespace="discord",
            auto_approve=False,
        )

        assert payload["items"][0]["auto_approve"] is False

    def test_an_attachment_reference_survives_a_replay_of_the_same_message(self):
        incoming = message()

        assert document_item_ref(incoming, pdf()) == "1234567890:attach-1"


class TestOutcomes:
    @pytest.mark.parametrize(
        ("item", "expected"),
        [
            ({"status": "pending", "review_status": "not_requested"}, "working"),
            ({"status": "completed", "review_status": "needs_review"}, "needs_review"),
            ({"status": "completed", "review_status": "approved"}, "published"),
            ({"status": "partial_success", "review_status": "needs_review"}, "partial"),
            ({"status": "failed", "review_status": "not_requested"}, "failed"),
            ({"status": "completed", "review_status": "duplicate"}, "duplicate"),
            (
                {
                    "status": "completed",
                    "review_status": "needs_review",
                    "disposition": "linked_existing",
                },
                "duplicate",
            ),
        ],
    )
    def test_an_item_reduces_to_the_one_thing_a_reader_cares_about(self, item, expected):
        assert item_outcome(item) == expected

    def test_a_receipt_is_summarised_by_its_least_happy_item(self):
        receipt = {
            "items": [
                {"status": "completed", "review_status": "approved"},
                {"status": "failed", "review_status": "not_requested"},
            ]
        }

        # A tick beside a failure would be a lie about what happened.
        assert receipt_outcome(receipt) == "failed"

    def test_a_receipt_is_settled_only_once_every_item_is(self):
        working = {"items": [{"status": "pending", "review_status": "not_requested"}]}
        done = {"items": [{"status": "completed", "review_status": "needs_review"}]}

        assert receipt_settled(working) is False
        assert receipt_settled(done) is True
        assert receipt_settled({"items": []}) is False


class TestReplies:
    def test_a_known_failure_is_always_explained_in_vietnamese(self):
        assert "tường phí" in describe_error("PAYWALL", "vi")
        assert "tường phí" in describe_error("PAYWALL", "en")

    def test_an_unknown_code_is_named_rather_than_guessed_at(self):
        text = describe_error("SOME_NEW_CODE", "en")

        assert "SOME_NEW_CODE" in text
        assert "lỗi phía hệ thống" in text

    def test_the_summary_names_each_item_and_what_was_left_out(self):
        receipt = {
            "items": [
                {
                    "ordinal": 1,
                    "normalized_url": "https://example.com/a",
                    "status": "failed",
                    "review_status": "not_requested",
                    "error_code": "ACCESS_DENIED",
                },
                {
                    "ordinal": 2,
                    "normalized_url": "https://example.com/b",
                    "status": "completed",
                    "review_status": "needs_review",
                },
            ]
        }

        summary = summarize_receipt(receipt, ["notes.docx: hệ thống chỉ thu thập tệp PDF"])

        assert "https://example.com/a" in summary
        assert "từ chối trình đọc tự động" in summary
        assert "đang chờ duyệt" in summary
        assert "notes.docx" in summary

    def test_the_summary_reports_related_gaps_once_in_the_channel_language(self):
        gap = {
            "id": "gap-1",
            "title": "Expand coverage for agent memory",
            "concept_key": "agent-memory",
            "coverage_count": 1,
        }
        receipt = {
            "items": [
                {
                    "ordinal": 1,
                    "normalized_url": "https://example.com/a",
                    "status": "completed",
                    "review_status": "approved",
                    "knowledge_gaps": [gap],
                },
                {
                    "ordinal": 2,
                    "normalized_url": "https://example.com/b",
                    "status": "completed",
                    "review_status": "approved",
                    "knowledge_gaps": [gap],
                },
            ]
        }

        summary = summarize_receipt(receipt, [], "vi")

        assert "Đã phát hiện khoảng trống tri thức" in summary
        assert summary.count("Expand coverage for agent memory") == 1
        assert "1 nguồn đã duyệt" in summary


class TestRateLimit:
    def test_a_user_is_bounded_within_the_window(self):
        limiter = PerUserRateLimit(limit=2, window_seconds=60)

        assert limiter.allow("user-1", 0.0) is True
        assert limiter.allow("user-1", 1.0) is True
        assert limiter.allow("user-1", 2.0) is False

    def test_the_budget_returns_once_the_window_passes(self):
        limiter = PerUserRateLimit(limit=1, window_seconds=60)
        limiter.allow("user-1", 0.0)

        assert limiter.allow("user-1", 59.0) is False
        assert limiter.allow("user-1", 61.0) is True

    def test_one_noisy_user_does_not_block_another(self):
        limiter = PerUserRateLimit(limit=1, window_seconds=60)
        limiter.allow("user-1", 0.0)

        assert limiter.allow("user-2", 0.0) is True


class TestConfiguration:
    def test_a_gateway_without_an_allowlist_refuses_to_start(self, monkeypatch, tmp_path):
        from app.config import load_config

        monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
        monkeypatch.setenv("RESEARCH_API_TOKEN", "service-token")
        monkeypatch.delenv("DISCORD_ALLOWED_GUILD_IDS", raising=False)
        monkeypatch.delenv("DISCORD_ALLOWED_CHANNEL_IDS", raising=False)

        config = load_config()

        assert config.configured is False
        assert "DISCORD_ALLOWED_GUILD_IDS" in config.missing()

    def test_a_file_mounted_secret_is_preferred_over_the_environment(self, monkeypatch, tmp_path):
        from app.config import load_config

        monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
        (tmp_path / "discord_bot_token").write_text("token-from-file\n")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "token-from-environment")
        monkeypatch.setenv("RESEARCH_API_TOKEN", "service-token")
        monkeypatch.setenv("DISCORD_ALLOWED_GUILD_IDS", "guild-1")
        monkeypatch.setenv("DISCORD_ALLOWED_CHANNEL_IDS", "channel-1, channel-2")

        config = load_config()

        # A file-mounted secret does not appear in `docker inspect` or a process listing.
        assert config.discord_token == "token-from-file"
        assert config.configured is True
        assert config.channel_ids == frozenset({"channel-1", "channel-2"})
        # Nội dung từ kênh chat là dữ liệu không tin cậy: tự duyệt phải được bật có chủ đích.
        assert config.auto_approve_links is False

    def test_guarded_auto_approval_setting_can_be_enabled(self, monkeypatch, tmp_path):
        from app.config import load_config

        monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
        monkeypatch.setenv("RESEARCH_API_TOKEN", "service-token")
        monkeypatch.setenv("DISCORD_ALLOWED_GUILD_IDS", "guild-1")
        monkeypatch.setenv("DISCORD_ALLOWED_CHANNEL_IDS", "channel-1")
        monkeypatch.setenv("DISCORD_AUTO_APPROVE_LINKS", "true")

        assert load_config().auto_approve_links is True



def test_gateway_never_pings_from_source_derived_text(monkeypatch, tmp_path):
    from app.bot import IntakeGatewayClient
    from app.config import load_config

    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("RESEARCH_API_TOKEN", "service-token")
    monkeypatch.setenv("DISCORD_ALLOWED_GUILD_IDS", "guild-1")
    monkeypatch.setenv("DISCORD_ALLOWED_CHANNEL_IDS", "channel-1")
    mentions = IntakeGatewayClient(load_config()).allowed_mentions
    assert not (mentions.everyone or mentions.roles or mentions.users or mentions.replied_user)
