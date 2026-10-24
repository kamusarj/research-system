import re

import pytest

from app.core.config import settings
from app.core.runtime_controls import rate_limiter
from app.models import AuditEvent, DocumentAIEditProposal, DocumentSourceVersion
from app.schemas.documents import DocumentInstantEditRequest
from app.services.document_instant_edit import (
    classify_edit_risk,
    instant_edit_document,
    is_standalone_latex_document,
    output_follows_required_contract,
)
from app.services.object_storage import DocumentError


class InstantEditProviderDouble:
    name = "instant-edit-test"
    version = "test"

    def __init__(self, replacement="A clearer sentence."):
        self.replacement = replacement
        self.prompts = []

    def complete_json(self, prompt, schema):
        self.prompts.append(prompt)
        return schema(replacement_text=self.replacement, explanation="Improved clarity.")

    def enrich(self, title, content):  # pragma: no cover - protocol compatibility only
        raise NotImplementedError


class MalformedInstantEditProvider(InstantEditProviderDouble):
    def complete_json(self, prompt, schema):
        raise IndexError("provider returned no choices")


class TokenPreservingInstantEditProvider(InstantEditProviderDouble):
    def complete_json(self, prompt, schema):
        self.prompts.append(prompt)
        email = re.search(r"\[RS_REDACTED_EMAIL_\d+\]", prompt)
        phone = re.search(r"\[RS_REDACTED_PHONE_\d+\]", prompt)
        assert email and phone
        replacement = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            f"\\noindent Contact: {email.group(0)} -- {phone.group(0)}\n"
            "\\end{document}"
        )
        return schema(replacement_text=replacement, explanation="Preserved contact values.")


def test_instant_edit_returns_anchored_patch_and_does_not_persist(db):
    runtime = InstantEditProviderDouble()
    source = "Before. Original sentence. After owner@example.com"
    start = source.index("Original")
    before = (
        db.query(DocumentAIEditProposal).count(),
        db.query(DocumentSourceVersion).count(),
        db.query(AuditEvent).count(),
    )

    result = instant_edit_document(
        DocumentInstantEditRequest(
            source=source,
            source_revision="draft-abc123",
            selection_start=start,
            selection_end=start + len("Original sentence."),
            action="improve",
            provider="deepseek",
        ),
        runtime=runtime,
    )

    assert result.source_revision == "draft-abc123"
    assert result.selection_start == start
    assert result.original_text_hash == (
        "b7e8a30184dc4fab8f1e3765eb2f535047c8191486504ef4b59df58a6e0d425f"
    )
    assert result.replacement_text == "A clearer sentence."
    assert result.risk == "low"
    assert result.auto_apply_allowed is False
    assert "INSTRUCTION is the user's required transformation" in runtime.prompts[0]
    assert "Apply it to ALL of SELECTED_TEXT" in runtime.prompts[0]
    assert "owner@example.com" not in runtime.prompts[0]
    assert before == (
        db.query(DocumentAIEditProposal).count(),
        db.query(DocumentSourceVersion).count(),
        db.query(AuditEvent).count(),
    )


def test_protected_content_is_review_only():
    risk, warnings = classify_edit_risk("Latency improved by 23% [4] with $x^2$.", "shorten", None)

    assert risk == "high"
    assert set(warnings) >= {
        "protected_numbers",
        "protected_citations",
        "protected_code_or_formula",
    }

    expand_risk, expand_warnings = classify_edit_risk("A plain claim.", "expand", None)
    assert expand_risk == "medium"
    assert expand_warnings == ["expansion_may_add_claims"]


def test_instant_edit_endpoint_returns_typed_patch(client, monkeypatch):
    runtime = InstantEditProviderDouble("Câu văn rõ ràng hơn.")
    monkeypatch.setattr("app.services.document_instant_edit.provider", lambda _name: runtime)

    response = client.post(
        "/api/v1/documents/edit-in-place",
        json={
            "source": "Câu văn chưa rõ.",
            "source_revision": "draft-1",
            "selection_start": 0,
            "selection_end": 16,
            "action": "improve",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["replacement_text"] == "Câu văn rõ ràng hơn."
    assert payload["source_revision"] == "draft-1"
    assert payload["auto_apply_allowed"] is False
    assert payload["provider_name"] == "deepseek"
    assert payload["model_name"] == "instant-edit-test"


def test_custom_format_conversion_is_mandatory_and_exact_no_change_is_typed():
    source = "Robot uses a camera."
    latex = "\\documentclass{article}\n\\begin{document}\nRobot uses a camera.\n\\end{document}"
    runtime = InstantEditProviderDouble(latex)
    result = instant_edit_document(
        DocumentInstantEditRequest(
            source=source,
            source_revision="draft-latex",
            selection_start=0,
            selection_end=len(source),
            action="custom",
            instruction="chuyển toàn bộ qua latex cho tôi",
            source_format="tex",
        ),
        runtime=runtime,
    )

    assert result.replacement_text == latex
    assert result.auto_apply_allowed is False
    assert "chuyển toàn bộ qua latex cho tôi" in runtime.prompts[0]
    assert "convert the complete selection accordingly" in runtime.prompts[0]
    assert "complete standalone LaTeX document" in runtime.prompts[0]
    assert output_follows_required_contract(
        DocumentInstantEditRequest(
            source=source,
            source_revision="draft-latex-check",
            selection_start=0,
            selection_end=len(source),
            action="custom",
            instruction="convert to LaTeX",
        ),
        "convert to LaTeX",
        latex,
    )

    with pytest.raises(DocumentError) as caught:
        instant_edit_document(
            DocumentInstantEditRequest(
                source=source,
                source_revision="draft-same",
                selection_start=0,
                selection_end=len(source),
                action="improve",
            ),
            runtime=InstantEditProviderDouble(source),
        )
    assert caught.value.code == "AI_EDIT_NO_CHANGE"


def test_whole_source_latex_edit_rejects_explanation_instead_of_raw_source():
    source = (
        "\\documentclass{article}\n\\begin{document}\n\\textbf{NGUYỄN MINH AN}\n\\end{document}"
    )
    explanation = (
        'Tôi sẽ giúp bạn thay đổi tên trong CV từ "Nguyễn Minh An" thành "Bùi Hoàng Linh".\n\n'
        "**Vị trí cần thay đổi:**\n\n"
        "```latex\n\\textbf{BÙI HOÀNG LINH}\n```"
    )
    request = DocumentInstantEditRequest(
        source=source,
        source_revision="draft-cv-rename",
        selection_start=0,
        selection_end=len(source),
        action="custom",
        instruction="sửa tên thành Bùi Hoàng Linh",
        source_format="latex",
    )

    with pytest.raises(DocumentError) as caught:
        instant_edit_document(request, runtime=InstantEditProviderDouble(explanation))

    assert caught.value.code == "AI_RESPONSE_INVALID"
    assert not is_standalone_latex_document(explanation)


def test_whole_source_latex_rename_accepts_only_a_complete_updated_document():
    source = (
        "% !TeX program = xelatex\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\textbf{NGUYỄN MINH AN}\n"
        "\\end{document}\n"
    )
    replacement = source.replace("NGUYỄN MINH AN", "BÙI HOÀNG LINH")
    request = DocumentInstantEditRequest(
        source=source,
        source_revision="draft-cv-rename-valid",
        selection_start=0,
        selection_end=len(source),
        action="custom",
        instruction="sửa tên thành Bùi Hoàng Linh",
        source_format="latex",
    )
    runtime = InstantEditProviderDouble(replacement)

    result = instant_edit_document(request, runtime=runtime)

    assert result.replacement_text == replacement
    assert result.auto_apply_allowed is False
    assert is_standalone_latex_document(replacement)
    assert "complete current standalone LaTeX source" in runtime.prompts[0]
    assert "no Markdown fence, explanation, preface or trailing commentary" in runtime.prompts[0]


def test_cloud_redaction_tokens_restore_sensitive_values_before_patch_review():
    email = "owner@example.com"
    phone = "+84 901 234 567"
    source = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        f"Contact: {email} -- {phone}\n"
        "\\end{document}"
    )
    runtime = TokenPreservingInstantEditProvider()

    result = instant_edit_document(
        DocumentInstantEditRequest(
            source=source,
            source_revision="draft-sensitive-cv",
            selection_start=0,
            selection_end=len(source),
            action="custom",
            instruction="sửa bố cục nhưng giữ nguyên thông tin liên hệ",
            source_format="latex",
        ),
        runtime=runtime,
    )

    assert email in result.replacement_text
    assert phone in result.replacement_text
    assert "REDACTED" not in result.replacement_text
    assert email not in runtime.prompts[0]
    assert phone not in runtime.prompts[0]
    assert "[RS_REDACTED_EMAIL_" in runtime.prompts[0]
    assert "[RS_REDACTED_PHONE_" in runtime.prompts[0]
    assert "cloud_redaction_applied" in result.warnings


@pytest.mark.parametrize(
    "replacement",
    [
        "\\documentclass{article}\n\\begin{document}[REDACTED_EMAIL]\\end{document}",
        "\\documentclass{article}\n\\begin{document}[RS_REDACTED_PHONE_999]\\end{document}",
    ],
)
def test_instant_edit_rejects_provider_redaction_markers(replacement):
    source = "\\documentclass{article}\n\\begin{document}Contact\\end{document}"
    with pytest.raises(DocumentError) as caught:
        instant_edit_document(
            DocumentInstantEditRequest(
                source=source,
                source_revision="draft-marker-leak",
                selection_start=0,
                selection_end=len(source),
                action="custom",
                instruction="fix the document",
                source_format="latex",
            ),
            runtime=InstantEditProviderDouble(replacement),
        )

    assert caught.value.code == "AI_RESPONSE_INVALID"


@pytest.mark.parametrize(
    "replacement",
    [
        "Preface\n\\documentclass{article}\n\\begin{document}X\\end{document}",
        "\\documentclass{article}\n\\begin{document}X",
        "\\documentclass{article}\n\\begin{document}X\\end{document}\nMore help follows.",
        "```latex\n\\documentclass{article}\n\\begin{document}X\\end{document}\n```",
    ],
)
def test_standalone_latex_document_rejects_non_source_wrappers(replacement):
    assert not is_standalone_latex_document(replacement)


def test_malformed_provider_payload_returns_typed_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_instant_edit.provider",
        lambda _name: MalformedInstantEditProvider(),
    )

    response = client.post(
        "/api/v1/documents/edit-in-place",
        json={
            "source": "Câu văn chưa rõ.",
            "source_revision": "draft-1",
            "selection_start": 0,
            "selection_end": 16,
            "action": "improve",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_RESPONSE_INVALID"


def test_instant_edit_rejects_invalid_ranges_and_missing_custom_instruction(client):
    outside = client.post(
        "/api/v1/documents/edit-in-place",
        json={
            "source": "short",
            "source_revision": "draft-1",
            "selection_start": 0,
            "selection_end": 10,
            "action": "improve",
        },
    )
    missing_instruction = client.post(
        "/api/v1/documents/edit-in-place",
        json={
            "source": "short",
            "source_revision": "draft-1",
            "selection_start": 0,
            "selection_end": 5,
            "action": "custom",
        },
    )

    assert outside.status_code == 422
    assert missing_instruction.status_code == 422


def test_instant_edit_uses_the_bounded_chat_rate_policy(client, monkeypatch):
    rate_limiter.clear()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_chat_per_window", 1)
    payload = {
        "source": "short",
        "source_revision": "draft-1",
        "selection_start": 0,
        "selection_end": 10,
        "action": "improve",
    }

    assert client.post("/api/v1/documents/edit-in-place", json=payload).status_code == 422
    limited = client.post("/api/v1/documents/edit-in-place", json=payload)

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
