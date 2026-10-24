export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
let csrfCookieName = "research_csrf";

export function setCsrfCookieName(value: string) {
  csrfCookieName = value;
}

function cookieValue(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie.split("; ").find((value) => value.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : null;
}

export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

const apiErrorMessages: Record<string, string> = {
  CHAT_API_KEY_INVALID: "Không xác thực được API key. Hãy kiểm tra khóa, nhà cung cấp đã chọn hoặc tạo khóa mới; tài khoản và IP cũng cần được phép truy cập.",
  CHAT_API_ACCESS_DENIED: "API từ chối quyền truy cập. Hãy kiểm tra quyền của khóa/dự án, mô hình và giới hạn khu vực hoặc IP.",
  CHAT_CREDIT_EXHAUSTED: "Tài khoản API chưa có hoặc đã hết credit. Hãy nạp số dư tại nhà cung cấp rồi kiểm tra lại.",
  CHAT_SPEND_LIMIT_REACHED: "Tài khoản hoặc dự án đã chạm giới hạn chi tiêu API. Hãy kiểm tra và điều chỉnh hạn mức tại nhà cung cấp.",
  CHAT_USAGE_LIMIT_REACHED: "Tài khoản đã chạm hạn mức sử dụng API được cấp. Hãy liên hệ nhà cung cấp để tăng hạn mức.",
  CHAT_QUOTA_EXCEEDED: "API không còn hạn mức sử dụng. Hãy kiểm tra credit, thanh toán và hạn mức tài khoản/dự án tại nhà cung cấp.",
  CHAT_MODEL_UNAVAILABLE: "Không tìm thấy mô hình hoặc API key này chưa được cấp quyền sử dụng. Hãy chọn mô hình khác hoặc kiểm tra quyền tại nhà cung cấp.",
  CHAT_MODEL_INCOMPATIBLE: "Mô hình không hỗ trợ cấu hình chat hoặc gọi công cụ của ứng dụng. Hãy chọn mô hình khác.",
  CHAT_PROVIDER_REQUEST_REJECTED: "Nhà cung cấp từ chối cấu hình yêu cầu. Hãy chọn mô hình khác; nếu vẫn lỗi, liên hệ quản trị viên.",
  CHAT_PROVIDER_RATE_LIMITED: "API đang giới hạn tốc độ yêu cầu, không đồng nghĩa hết credit. Hãy đợi một chút rồi thử lại.",
  CHAT_PROVIDER_TIMEOUT: "Nhà cung cấp phản hồi quá chậm. Chưa thể xác nhận kết nối; hãy thử lại sau.",
  CHAT_PROVIDER_UNAVAILABLE: "Chưa thể kết nối với nhà cung cấp AI. Hãy kiểm tra mạng hoặc thử lại sau.",
  CHAT_PROVIDER_FAILED: "Nhà cung cấp trả về phản hồi không hợp lệ. Chưa thể xác nhận kết nối; hãy thử lại sau.",
  CHAT_CLI_LIMIT_REACHED: "CLI trên máy chủ (Claude Code, Codex hoặc Antigravity) đã hết quota của gói đăng ký trong khung giờ này. Hãy đợi quota làm mới hoặc chọn AI khác.",
  CHAT_CLI_LOGIN_REQUIRED: "CLI trên máy chủ chưa đăng nhập hoặc phiên đăng nhập đã hết hạn. Chủ máy cần đăng nhập lại CLI đó.",
  CHAT_PERSONAL_KEY_REQUIRED: "Hãy nhập lại API key cá nhân để tiếp tục cuộc trò chuyện này.",
  CHAT_CREDENTIAL_MISMATCH: "Hãy tạo cuộc trò chuyện dùng API cá nhân để sử dụng khóa của bạn.",
  FEATURE_DISABLED: "Nghiên cứu sâu chưa được bật trên máy chủ này.",
  RESEARCH_RUN_ACTIVE: "Bạn đang có một lượt nghiên cứu chưa hoàn tất. Hãy chờ hoặc hủy nó trước.",
  RESEARCH_DAILY_BUDGET_EXCEEDED: "Bạn đã dùng hết số lượt nghiên cứu sâu hôm nay.",
  RESEARCH_REPORT_NOT_READY: "Báo cáo chưa sẵn sàng.",
  CROSS_SITE_REQUEST_BLOCKED: "Yêu cầu từ trang web khác bị chặn.",
  AUTH_REQUIRED: "Bạn cần đăng nhập để tiếp tục.",
  FORBIDDEN: "Bạn không có quyền thực hiện thao tác này.",
  NOT_FOUND: "Không tìm thấy dữ liệu được yêu cầu.",
  VALIDATION_ERROR: "Dữ liệu gửi lên chưa hợp lệ.",
  INVALID_URL: "URL không hợp lệ hoặc không thể truy cập công khai.",
  UNSUPPORTED_SOURCE: "Loại nguồn này chưa được hỗ trợ.",
  SOURCE_NOT_FOUND: "Không tìm thấy nguồn.",
  ACCESS_DENIED: "Nguồn đã từ chối yêu cầu truy cập.",
  RATE_LIMITED: "Đã chạm giới hạn tần suất. Hãy thử lại sau.",
  FETCH_TIMEOUT: "Nguồn phản hồi quá chậm. Hãy thử lại sau.",
  FETCH_FAILED: "Không thể tải nguồn.",
  EXTRACTION_FAILED: "Không thể trích xuất nội dung từ nguồn.",
  EMPTY_CONTENT: "Nguồn không có nội dung đọc được.",
  CONTENT_TOO_LARGE: "Nội dung vượt quá giới hạn dung lượng.",
  UNSUPPORTED_CONTENT_TYPE: "Định dạng nội dung này chưa được hỗ trợ.",
  AI_PROVIDER_NOT_CONFIGURED: "Chưa cấu hình nhà cung cấp AI.",
  AI_PROVIDER_AUTH_FAILED: "Nhà cung cấp AI từ chối thông tin xác thực.",
  AI_PROVIDER_RATE_LIMITED: "Nhà cung cấp AI đang giới hạn tần suất.",
  AI_PROVIDER_UNAVAILABLE: "Không thể kết nối với nhà cung cấp AI.",
  AI_PROVIDER_ERROR: "Nhà cung cấp AI trả về lỗi.",
  AI_RESPONSE_INVALID: "Phản hồi AI không đúng cấu trúc mong đợi.",
  STORAGE_UNAVAILABLE: "Kho lưu trữ hiện chưa sẵn sàng.",
  DATABASE_ERROR: "Cơ sở dữ liệu không thể hoàn tất cập nhật.",
  DOCUMENT_NOT_FOUND: "Không tìm thấy tài liệu.",
  DOCUMENT_TOO_LARGE: "Tài liệu vượt quá giới hạn dung lượng.",
  INVALID_DOCUMENT: "Tài liệu chưa hợp lệ.",
  GRAPH_CHANGE_NOT_FOUND: "Không tìm thấy bộ thay đổi đồ thị.",
  INTERNAL_ERROR: "Có lỗi ngoài dự kiến khi xử lý yêu cầu.",
  PASSWORD_INCORRECT: "Mật khẩu hiện tại không đúng.",
  WORKER_LEASE_EXPIRED: "Tác vụ bị gián đoạn nhiều lần và đã dừng. Hãy thử lại.",
  COLLECTOR_RUN_FAILED: "Không thể thu thập nguồn tin này.",
  CSRF_REQUIRED: "Phiên làm việc cần được tải lại. Hãy tải lại trang rồi thử lại.",
  internal_error: "Có lỗi ngoài dự kiến khi xử lý yêu cầu.",
  request_error: "Không thể hoàn tất yêu cầu.",
};

// Backend gắn các mã chung này cho mọi HTTPException theo mã trạng thái; với lỗi HTTP chúng
// không mang nghĩa "nguồn" mà là quyền/không tìm thấy nói chung.
const statusOnlyCodes = new Set(["ACCESS_DENIED", "SOURCE_NOT_FOUND", "INVALID_REQUEST"]);

/** Chuyển lỗi kỹ thuật thành thông báo tiếng Việt ổn định cho giao diện. */
export function vietnameseApiErrorMessage(code: string | null | undefined, status?: number): string {
  if (code && apiErrorMessages[code] && !(status && statusOnlyCodes.has(code))) {
    return apiErrorMessages[code];
  }
  if (status === 401) return "Bạn cần đăng nhập để tiếp tục.";
  if (status === 403) return "Bạn không có quyền thực hiện thao tác này.";
  if (status === 404) return "Không tìm thấy dữ liệu được yêu cầu.";
  if (status === 409) return "Dữ liệu đã thay đổi hoặc đang xung đột. Hãy tải lại rồi thử lại.";
  if (status === 422) return "Dữ liệu gửi lên chưa hợp lệ.";
  if (status && status >= 500) return "Máy chủ chưa thể hoàn tất yêu cầu. Hãy thử lại sau.";
  return status ? `Không thể hoàn tất yêu cầu (HTTP ${status}).` : "Không thể hoàn tất yêu cầu.";
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = cookieValue(csrfCookieName);
    if (token) headers.set("X-CSRF-Token", token);
  }
  return fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
}

/** Sự kiện phát khi API báo phiên đã hết hạn để AuthProvider đưa người dùng về màn đăng nhập. */
export const AUTH_EXPIRED_EVENT = "research:auth-expired";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  if (response.status === 401 && !path.startsWith("/auth/") && typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      vietnameseApiErrorMessage(payload?.error?.code, response.status),
      payload?.error?.code ?? "request_error",
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
