"""Phản hồi tiếng Việt cho kênh Discord, dựa trên kết quả do API quyết định."""

from __future__ import annotations

from app.gateway import ItemOutcome

Locale = str

OUTCOME_TEXT: dict[str, dict[Locale, str]] = {
    "published": {
        "vi": "đã xuất bản vào kho tri thức",
    },
    "needs_review": {
        "vi": "đã thu thập, đang chờ duyệt",
    },
    "partial": {
        "vi": "đã thu thập, nhưng một phần nội dung không lấy được",
    },
    "duplicate": {
        "vi": "đã có sẵn trong thư viện",
    },
    "failed": {
        "vi": "không thu thập được",
    },
    "working": {
        "vi": "đang xử lý",
    },
}

# Chỉ mô tả lỗi mà người trong kênh có thể tự xử lý. Lỗi còn lại thuộc người vận hành.
ERROR_ADVICE: dict[str, dict[Locale, str]] = {
    "INVALID_URL": {
        "vi": "địa chỉ đó không phải liên kết http(s) công khai",
    },
    "SOURCE_NOT_FOUND": {
        "vi": "trang không còn tồn tại — hãy thử bản lưu trữ",
    },
    "AUTH_REQUIRED": {
        "vi": "trang yêu cầu đăng nhập, ở đây chỉ dùng được trang công khai",
    },
    "ACCESS_DENIED": {
        "vi": "trang từ chối trình đọc tự động — hãy tải nội dung lên dạng tệp",
    },
    "BOT_PROTECTED": {
        "vi": "trang trả về màn hình chống bot thay vì bài viết",
    },
    "PAYWALL": {
        "vi": "bài viết nằm sau tường phí",
    },
    "CONSENT_WALL": {
        "vi": "trang trả về thông báo cookie thay vì bài viết",
    },
    "JS_RENDER_REQUIRED": {
        "vi": "trang cần JavaScript, nên chỉ lấy được phần tóm tắt",
    },
    "PDF_SCANNED_OCR_DISABLED": {
        "vi": "tệp PDF đó là bản quét và máy chủ đang tắt OCR",
    },
    "CONTENT_TOO_LARGE": {
        "vi": "nguồn vượt quá giới hạn dung lượng",
    },
    "UNSUPPORTED_CONTENT_TYPE": {
        "vi": "địa chỉ đó trả về tệp chứ không phải bài viết",
    },
    "TRANSCRIPT_UNAVAILABLE": {
        "vi": "chỉ lấy được siêu dữ liệu công khai — hãy thêm bản chép lời trong ứng dụng web",
    },
}

GENERIC_FAILURE: dict[Locale, str] = {
    "vi": "có lỗi phía hệ thống",
}

NOT_PERMITTED: dict[Locale, str] = {
    "vi": "Kênh này không nằm trong danh sách cho phép thu thập.",
}

NOTHING_TO_COLLECT: dict[Locale, str] = {
    "vi": "Không tìm thấy liên kết công khai hoặc tệp PDF. Dùng `/help` để xem hướng dẫn.",
}

GAP_HEADING: dict[Locale, str] = {
    "vi": "Đã phát hiện khoảng trống tri thức",
}

GAP_COVERAGE: dict[Locale, str] = {
    "vi": "nguồn đã duyệt",
}

MAX_GAP_ALERTS_PER_REPLY = 5


def describe_outcome(outcome: ItemOutcome, locale: Locale = "vi") -> str:
    text = OUTCOME_TEXT.get(outcome, OUTCOME_TEXT["working"])
    return text["vi"]


def describe_error(code: str | None, locale: Locale = "vi") -> str:
    if not code:
        return GENERIC_FAILURE["vi"]
    advice = ERROR_ADVICE.get(code)
    if advice is None:
        # Giữ mã lỗi để người vận hành có thể tra cứu thay vì đoán nguyên nhân.
        return f"{GENERIC_FAILURE['vi']} ({code})"
    return advice["vi"]


def summarize_receipt(receipt: dict, plan_skipped: list[str], locale: Locale = "vi") -> str:
    """One reply per message, naming each item's fate and anything that was left out."""

    from app.gateway import item_outcome

    lines: list[str] = []
    for item in receipt.get("items", []):
        label = item.get("normalized_url") or f"tệp đính kèm {item.get('ordinal')}"
        outcome = item_outcome(item)
        text = describe_outcome(outcome, locale)
        if outcome == "failed":
            text = f"{text} — {describe_error(item.get('error_code'), locale)}"
        lines.append(f"• {label}: {text}")
    for skipped in plan_skipped:
        lines.append(f"• {skipped}")
    gaps: dict[str, dict] = {}
    for item in receipt.get("items", []):
        for gap in item.get("knowledge_gaps") or []:
            gap_id = str(gap.get("id") or gap.get("concept_key") or "")
            if gap_id:
                gaps.setdefault(gap_id, gap)
    if gaps:
        lines.append("")
        lines.append(f"⚠️ {GAP_HEADING['vi']}:")
        for gap in list(gaps.values())[:MAX_GAP_ALERTS_PER_REPLY]:
            title = str(gap.get("title") or gap.get("concept_key") or "—")
            coverage = int(gap.get("coverage_count") or 0)
            coverage_label = GAP_COVERAGE["vi"]
            lines.append(f"• {title} ({coverage} {coverage_label})")
        hidden = len(gaps) - MAX_GAP_ALERTS_PER_REPLY
        if hidden > 0:
            lines.append(f"• +{hidden}")
    return "\n".join(lines)
