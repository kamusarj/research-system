"""Nội dung hướng dẫn tiếng Việt có thể kiểm thử mà không cần kết nối Discord."""

from __future__ import annotations

from collections.abc import Mapping

Locale = str

COMMAND_NAMES: tuple[str, ...] = (
    "help",
    "guide",
    "sources",
    "ping",
    "pin",
    "submit",
    "status",
)

COMMAND_DESCRIPTIONS: Mapping[str, Mapping[Locale, str]] = {
    "help": {
        "vi": "Xem toàn bộ lệnh và cách bot hoạt động",
    },
    "guide": {
        "vi": "Xem hướng dẫn từ nguồn đến đồ thị tri thức",
    },
    "sources": {
        "vi": "Xem loại nguồn được hỗ trợ và giới hạn",
    },
    "ping": {
        "vi": "Kiểm tra bot có đang phản hồi hay không",
    },
    "pin": {
        "vi": "Ghim một tin nhắn trong kênh hiện tại",
    },
    "submit": {
        "vi": "Nhập thủ công một liên kết công khai (tùy chọn)",
    },
    "status": {
        "vi": "Xem kết quả của một tin nhắn Discord đã gửi",
    },
}

HELP_TEXT: Mapping[Locale, str] = {
    "vi": """**Research Assistant — danh sách lệnh**

`/help` — xem danh sách này
`/guide` — xem từng bước từ nguồn đến đồ thị tri thức
`/sources` — loại nguồn được hỗ trợ và các giới hạn
`/ping` — kiểm tra bot đang phản hồi
`/pin message_id:<id>` — ghim tin nhắn trong kênh (cần quyền Ghim tin nhắn)
`/submit url:<link>` — cách nhập thủ công tùy chọn
`/status message_id:<id>` — xem lại kết quả của tin nhắn đã thu thập

**Cách nhanh nhất**
Không cần dùng `/submit`: chỉ cần gửi một hay nhiều link công khai, hoặc đính kèm PDF
trong kênh này. Bot tự thu thập và phản hồi: ⏳ đang xử lý · ✅ đã xuất bản · 📥 chờ
duyệt · ⚠️ một phần · ♻️ đã có · ❌ thất bại · 🚫 giới hạn.

Bot chỉ hoạt động trong máy chủ và kênh được cho phép. Dùng `/guide` nếu đây là lần đầu bạn
sử dụng.""",
}

GUIDE_TEXT: Mapping[Locale, str] = {
    "vi": """**Hướng dẫn sử dụng**

1. Gửi thẳng bài báo khoa học, GitHub, Facebook/Reel công khai hoặc PDF vào kênh. Bot tự
   tiếp nhận; `/submit` chỉ là cách thủ công tùy chọn.
2. Chờ biểu tượng `⏳`. Bot tạo biên nhận; hệ thống trích xuất, phân loại và chống trùng lặp.
3. Đọc kết quả: `✅` đã vào đồ thị quan hệ; `📥` cần duyệt trên web; `⚠️` cho biết
   phần nội dung còn thiếu và hành động tiếp theo.
4. Nếu mục đã duyệt tạo ra khoảng trống tri thức, bot sẽ thông báo ngay dưới kết quả.
5. Bật Chế độ nhà phát triển của Discord, sao chép ID tin nhắn rồi dùng `/status` để kiểm tra lại.
6. Khi cần ghim, dùng `/pin message_id:<id>`; cả bạn và bot phải có quyền
   **Ghim tin nhắn**.

Bot không tự áp dụng bộ thay đổi phân cấp và không vượt qua đăng nhập, tường phí
hay lớp chống bot.""",
}

SOURCES_TEXT: Mapping[Locale, str] = {
    "vi": """**Nguồn được hỗ trợ**

• Bài báo và trang web công khai
• Bài báo khoa học: DOI, arXiv và nhà xuất bản được hỗ trợ
• Kho mã GitHub công khai
• Bài đăng/Reel Facebook công khai (có thể chỉ lấy được siêu dữ liệu nếu thiếu bản chép lời)
• URL PDF hoặc tệp PDF đính kèm có văn bản; OCR phụ thuộc cấu hình máy chủ

**Giới hạn mỗi tin nhắn**
Tối đa 20 liên kết, 5 tệp PDF và 20 MB cho mỗi PDF. Nguồn cần đăng nhập, có tường phí
hoặc bị khóa vùng/chống bot sẽ trả về giới hạn rõ ràng. Bot không tự tải hoặc chép lời
nội dung Reel.""",
}

PING_TEXT: Mapping[Locale, str] = {
    "vi": "🏓 Bot đang phản hồi{latency}. Dùng `/help` để xem lệnh.",
}

COMMAND_ERROR: Mapping[Locale, str] = {
    "vi": "Không thể hoàn tất lệnh này. Hãy thử lại hoặc dùng `/help`.",
}

PIN_OPTION_DESCRIPTION: Mapping[Locale, str] = {
    "vi": "ID của tin nhắn trong kênh hiện tại",
}

PIN_RESULT: Mapping[str, Mapping[Locale, str]] = {
    "invalid_id": {
        "vi": "ID tin nhắn không hợp lệ. Hãy bật Chế độ nhà phát triển rồi sao chép ID tin nhắn.",
    },
    "caller_forbidden": {
        "vi": "Bạn cần quyền **Ghim tin nhắn** trong kênh này để dùng `/pin`.",
    },
    "bot_forbidden": {
        "vi": "Bot chưa có quyền **Ghim tin nhắn** trong kênh này.",
    },
    "not_found": {
        "vi": "Không tìm thấy tin nhắn đó trong kênh hiện tại.",
    },
    "already_pinned": {
        "vi": "📌 Tin nhắn này đã được ghim.",
    },
    "pinned": {
        "vi": "📌 Đã ghim tin nhắn.",
    },
    "failed": {
        "vi": "Discord không thể ghim tin nhắn này. Hãy kiểm tra quyền và thử lại.",
    },
}

PRESENCE_TEXT: Mapping[Locale, str] = {
    "vi": "/help • gửi liên kết để thu thập",
}


def localized(values: Mapping[Locale, str], locale: Locale) -> str:
    """Luôn trả về tiếng Việt; tham số locale chỉ được giữ để tương thích."""

    return values["vi"]


def command_description(name: str, locale: Locale) -> str:
    return localized(COMMAND_DESCRIPTIONS[name], locale)


def help_text(locale: Locale) -> str:
    return localized(HELP_TEXT, locale)


def guide_text(locale: Locale) -> str:
    return localized(GUIDE_TEXT, locale)


def sources_text(locale: Locale) -> str:
    return localized(SOURCES_TEXT, locale)


def ping_text(locale: Locale, latency_ms: int | None) -> str:
    latency = f" · {latency_ms} ms" if latency_ms is not None else ""
    return localized(PING_TEXT, locale).format(latency=latency)


def pin_option_description(locale: Locale) -> str:
    return localized(PIN_OPTION_DESCRIPTION, locale)


def pin_result(result: str, locale: Locale) -> str:
    return localized(PIN_RESULT[result], locale)
