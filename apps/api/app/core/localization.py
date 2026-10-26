"""Thông báo tiếng Việt ổn định dành cho các bề mặt sản phẩm."""

from __future__ import annotations

ERROR_MESSAGES = {
    "CHAT_API_KEY_INVALID": (
        "Không xác thực được API key. Hãy kiểm tra khóa, nhà cung cấp đã chọn hoặc tạo "
        "khóa mới; tài khoản và IP cũng cần được phép truy cập."
    ),
    "CHAT_API_ACCESS_DENIED": (
        "API từ chối quyền truy cập. Hãy kiểm tra quyền của khóa/dự án, mô hình và giới "
        "hạn khu vực hoặc IP."
    ),
    "CHAT_CREDIT_EXHAUSTED": (
        "Tài khoản API chưa có hoặc đã hết credit. Hãy nạp số dư tại nhà cung cấp rồi kiểm tra lại."
    ),
    "CHAT_SPEND_LIMIT_REACHED": (
        "Tài khoản hoặc dự án đã chạm giới hạn chi tiêu API. Hãy kiểm tra và điều chỉnh "
        "hạn mức tại nhà cung cấp."
    ),
    "CHAT_USAGE_LIMIT_REACHED": (
        "Tài khoản đã chạm hạn mức sử dụng API được cấp. Hãy liên hệ nhà cung cấp để tăng hạn mức."
    ),
    "CHAT_QUOTA_EXCEEDED": (
        "API không còn hạn mức sử dụng. Hãy kiểm tra credit, thanh toán và hạn mức tài "
        "khoản/dự án tại nhà cung cấp."
    ),
    "CHAT_MODEL_UNAVAILABLE": (
        "Không tìm thấy mô hình hoặc API key này chưa được cấp quyền sử dụng. Hãy chọn mô "
        "hình khác hoặc kiểm tra quyền tại nhà cung cấp."
    ),
    "CHAT_MODEL_INCOMPATIBLE": (
        "Mô hình không hỗ trợ cấu hình chat hoặc gọi công cụ của ứng dụng. Hãy chọn mô hình khác."
    ),
    "CHAT_PROVIDER_REQUEST_REJECTED": (
        "Nhà cung cấp từ chối cấu hình yêu cầu. Hãy chọn mô hình khác; nếu vẫn lỗi, liên "
        "hệ quản trị viên."
    ),
    "CHAT_PROVIDER_RATE_LIMITED": (
        "API đang giới hạn tốc độ yêu cầu, không đồng nghĩa hết credit. Hãy đợi một chút "
        "rồi thử lại."
    ),
    "CHAT_PROVIDER_TIMEOUT": (
        "Nhà cung cấp phản hồi quá chậm. Chưa thể xác nhận kết nối; hãy thử lại sau."
    ),
    "CHAT_PROVIDER_UNAVAILABLE": (
        "Chưa thể kết nối với nhà cung cấp AI. Hãy kiểm tra mạng hoặc thử lại sau."
    ),
    "CHAT_PROVIDER_FAILED": (
        "Nhà cung cấp trả về phản hồi không hợp lệ. Chưa thể xác nhận kết nối; hãy thử lại sau."
    ),
    "CHAT_PERSONAL_KEY_REQUIRED": "Hãy nhập lại API key cá nhân để tiếp tục cuộc trò chuyện này.",
    "CHAT_CREDENTIAL_MISMATCH": "Hãy tạo cuộc trò chuyện dùng API cá nhân để sử dụng khóa của bạn.",
    "AUTH_REQUIRED": "Bạn cần đăng nhập để tiếp tục.",
    "ACCESS_DENIED": "Bạn không có quyền thực hiện thao tác này.",
    "SOURCE_NOT_FOUND": "Không tìm thấy dữ liệu được yêu cầu.",
    "DOCUMENT_NOT_FOUND": "Không tìm thấy tài liệu.",
    "DOCUMENT_VERSION_NOT_FOUND": "Không tìm thấy phiên bản tài liệu.",
    "CHANGE_SET_NOT_FOUND": "Không tìm thấy bộ thay đổi đồ thị.",
    "MUTATION_NOT_FOUND": "Không tìm thấy thay đổi đồ thị.",
    "GRAPH_NODE_NOT_FOUND": "Không tìm thấy nút trong đồ thị.",
    "CHAT_SESSION_NOT_FOUND": "Không tìm thấy cuộc trò chuyện.",
    "CHAT_SCOPE_NOT_FOUND": "Không tìm thấy phạm vi trò chuyện.",
    "CHAT_MEDIA_NOT_FOUND": "Không tìm thấy tệp đa phương tiện của cuộc trò chuyện.",
    "UNSUPPORTED_CONTENT_TYPE": "Định dạng nội dung này chưa được hỗ trợ.",
    "RATE_LIMITED": "Đã chạm giới hạn tần suất. Hãy thử lại sau.",
    "INVALID_URL": "URL không hợp lệ hoặc không thể truy cập công khai.",
    "INVALID_REQUEST": "Dữ liệu gửi lên chưa hợp lệ.",
    "UNSUPPORTED_SOURCE": "Loại nguồn này chưa được hỗ trợ.",
    "BOT_PROTECTED": "Nguồn có lớp chống bot nên không thể đọc đầy đủ.",
    "PAYWALL": "Nguồn nằm sau tường phí.",
    "CONSENT_WALL": "Thông báo cookie hoặc khu vực đã che nội dung nguồn.",
    "JS_RENDER_REQUIRED": "Nguồn cần JavaScript để hiển thị đầy đủ.",
    "FETCH_TIMEOUT": "Nguồn phản hồi quá chậm. Hãy thử lại sau.",
    "FETCH_FAILED": "Không thể tải nguồn.",
    "DNS_FAILED": "Không phân giải được tên miền của nguồn.",
    "TLS_FAILED": "Chứng chỉ của nguồn không hợp lệ hoặc không đáng tin cậy.",
    "CONTENT_TOO_LARGE": "Nội dung vượt quá giới hạn dung lượng.",
    "EXTRACTION_FAILED": "Không thể trích xuất nội dung từ nguồn.",
    "EMPTY_CONTENT": "Nguồn không có nội dung đọc được.",
    "PDF_PARSE_FAILED": "Không thể đọc tệp PDF.",
    "PDF_SCANNED_OCR_DISABLED": "PDF là bản quét và OCR đang tắt.",
    "TRANSCRIPT_SOURCE_INVALID": "Không thể dùng bản chép lời cho loại nguồn này.",
    "TRANSCRIPT_UNAVAILABLE": "Nguồn chưa có bản chép lời.",
    "AI_PROVIDER_NOT_CONFIGURED": "Chưa cấu hình nhà cung cấp AI.",
    "AI_PROVIDER_AUTH_FAILED": "Nhà cung cấp AI từ chối thông tin xác thực.",
    "AI_PROVIDER_RATE_LIMITED": "Nhà cung cấp AI đang giới hạn tần suất.",
    "AI_PROVIDER_UNAVAILABLE": "Không thể kết nối với nhà cung cấp AI.",
    "AI_PROVIDER_ERROR": "Nhà cung cấp AI trả về lỗi.",
    "AI_RESPONSE_INVALID": "Phản hồi AI không đúng cấu trúc mong đợi.",
    "STORAGE_UNAVAILABLE": "Kho lưu trữ hiện chưa sẵn sàng.",
    "DATABASE_ERROR": "Cơ sở dữ liệu không thể hoàn tất cập nhật.",
    "DOCUMENT_TOO_LARGE": "Tài liệu vượt quá giới hạn dung lượng.",
    "DOCUMENT_EXTRACTION_FAILED": "Không thể trích xuất nội dung tài liệu.",
    "INTERNAL_ERROR": "Máy chủ chưa thể hoàn tất yêu cầu. Hãy thử lại sau.",
    "METRICS_NOT_CONFIGURED": "Chưa cấu hình xác thực cho dữ liệu giám sát.",
    "NEO4J_NOT_CONFIGURED": "Đã chọn Neo4j cho đồ thị nhưng chưa cấu hình kết nối.",
    "FEATURE_DISABLED": "Nghiên cứu sâu chưa được bật trên máy chủ này.",
    "RESEARCH_RUN_ACTIVE": "Bạn đang có một lượt nghiên cứu chưa hoàn tất. Hãy chờ hoặc hủy nó.",
    "RESEARCH_DAILY_BUDGET_EXCEEDED": "Bạn đã dùng hết số lượt nghiên cứu sâu hôm nay.",
    "RESEARCH_RUN_NOT_FOUND": "Không tìm thấy lượt nghiên cứu.",
    "RESEARCH_RUN_STATE": "Chỉ thử lại được lượt nghiên cứu đã thất bại.",
    "RESEARCH_REPORT_NOT_READY": "Báo cáo chưa sẵn sàng.",
    "RESEARCH_VARIANT_UNSUPPORTED": "Biến thể nghiên cứu không được hỗ trợ.",
    "KNOWLEDGE_GAP_NOT_FOUND": "Không tìm thấy khoảng trống tri thức.",
    "HOST_NOT_ALLOWED": "Tên máy chủ của yêu cầu không được chấp nhận.",
    "CROSS_SITE_REQUEST_BLOCKED": "Yêu cầu từ trang web khác bị chặn.",
    "CHATGPT_PLAN_DISABLED": "Tính năng dùng gói ChatGPT chưa được bật trên máy chủ này.",
    "CHATGPT_PLAN_NOT_CONNECTED": "Bạn chưa kết nối gói ChatGPT. Vào trang Tài khoản để kết nối.",
    "CHATGPT_PLAN_REAUTH_REQUIRED": (
        "Phiên ChatGPT đã hết hạn. Hãy kết nối lại trong trang Tài khoản."
    ),
    "CHATGPT_PLAN_SCOPE_MISSING": "Bạn chưa cho phép ứng dụng dùng gói ChatGPT. Hãy kết nối lại.",
    "CHATGPT_PLAN_CONSENT_DECLINED": "Bạn đã từ chối cho ứng dụng dùng gói ChatGPT.",
    "CHATGPT_PLAN_LIMIT_REACHED": (
        "Đã chạm hạn mức gói ChatGPT hoặc giới hạn riêng cho ứng dụng này. "
        "Xem và chỉnh ở ChatGPT → Cài đặt → Mức sử dụng."
    ),
    "CHATGPT_PLAN_NOT_ELIGIBLE": "Tài khoản ChatGPT này không được dùng gói cho ứng dụng.",
    "CHATGPT_PLAN_UNAVAILABLE": "ChatGPT tạm thời không phản hồi. Hãy thử lại sau.",
    "CHATGPT_PLAN_TIMEOUT": "ChatGPT trả lời quá lâu. Hãy thử lại.",
    "CHATGPT_PLAN_UNSUPPORTED": "Gói ChatGPT không hỗ trợ model hoặc tính năng của yêu cầu này.",
    "CHATGPT_PLAN_INCOMPLETE": "ChatGPT dừng giữa chừng trước khi trả lời xong.",
    "CHATGPT_PLAN_FAILED": "ChatGPT không hoàn tất yêu cầu.",
    "CHATGPT_PLAN_STATE_INVALID": (
        "Phiên kết nối ChatGPT đã hết hạn hoặc không hợp lệ. Hãy thử lại."
    ),
    "CHATGPT_PLAN_AUTH_FAILED": "ChatGPT không hoàn tất đăng nhập. Hãy thử kết nối lại.",
    "CHATGPT_PLAN_IDENTITY_INVALID": "Không xác minh được danh tính ChatGPT.",
    "CHATGPT_PLAN_ACCOUNT_MISMATCH": (
        "Đây là tài khoản ChatGPT khác tài khoản đã kết nối. Hãy xóa kết nối cũ trước."
    ),
    "CHATGPT_PLAN_MODEL_UNAVAILABLE": "Model này không có trong gói ChatGPT của bạn.",
    "CHATGPT_PLAN_OWNER_ONLY": (
        "Việc này dùng gói ChatGPT của người tạo; chỉ người đó mới chạy lại được."
    ),
    "CHATGPT_PLAN_VAULT_UNAVAILABLE": "Máy chủ chưa cấu hình khóa mã hóa cho kết nối ChatGPT.",
}


def product_error_message(code: str, status_code: int) -> str:
    """Trả về thông báo an toàn, không để lọt câu lỗi nội bộ bằng ngôn ngữ khác."""

    if code in ERROR_MESSAGES:
        return ERROR_MESSAGES[code]
    if status_code == 401:
        return ERROR_MESSAGES["AUTH_REQUIRED"]
    if status_code == 403:
        return ERROR_MESSAGES["ACCESS_DENIED"]
    if status_code == 404:
        return "Không tìm thấy dữ liệu được yêu cầu."
    if status_code == 409:
        return "Dữ liệu đang xung đột với trạng thái hiện tại. Hãy tải lại rồi thử lại."
    if status_code == 422:
        return ERROR_MESSAGES["INVALID_REQUEST"]
    if status_code >= 500:
        return ERROR_MESSAGES["INTERNAL_ERROR"]
    return "Không thể hoàn tất yêu cầu."
