import { api } from "@/lib/api";

export const CHATGPT_PLAN_PROVIDER = "chatgpt_plan";
export const CHATGPT_USAGE_URL = "https://chatgpt.com/settings/usage";
const WELCOME_KEY = "chatgpt-plan-welcomed";

export type ChatGPTPlanStatus = {
  enabled: boolean;
  mode: "local" | "partner";
  status: "not_connected" | "active" | "signed_out" | "reauth_required" | "plan_disabled";
  email: string | null;
  model: string | null;
  models: { slug: string; display_name: string }[];
  use_by_default: boolean;
  last_error_code: string | null;
  connected_at: string | null;
  last_used_at: string | null;
  usage_url: string;
};

export function getChatGPTPlan() {
  return api<ChatGPTPlanStatus>("/ai-connections/chatgpt");
}

/** Bắt đầu đăng nhập ChatGPT: máy chủ tạo state/PKCE rồi trả về trang đồng ý của OpenAI. */
export async function startChatGPTPlan(): Promise<string> {
  const { authorize_url } = await api<{ authorize_url: string }>("/ai-connections/chatgpt/start", { method: "POST" });
  return authorize_url;
}

export type CallbackParams = { state: string; code?: string; client_id?: string; error?: string };

/** Đọc tham số OAuth trả về; trả null nếu thiếu state (không phải callback hợp lệ). */
export function readCallbackParams(search: string): CallbackParams | null {
  const params = new URLSearchParams(search);
  const state = params.get("state");
  if (!state) return null;
  const pick = (name: string) => params.get(name) || undefined;
  return { state, code: pick("code"), client_id: pick("client_id"), error: pick("error") };
}

export function completeChatGPTPlan(params: CallbackParams) {
  return api<ChatGPTPlanStatus>("/ai-connections/chatgpt/complete", { method: "POST", body: JSON.stringify(params) });
}

export function updateChatGPTPlan(preferences: { model?: string; use_by_default?: boolean }) {
  return api<ChatGPTPlanStatus>("/ai-connections/chatgpt/preferences", { method: "POST", body: JSON.stringify(preferences) });
}

export function disconnectChatGPTPlan(forget = false) {
  return api<{ remote_revoked: boolean; connection: ChatGPTPlanStatus }>("/ai-connections/chatgpt/disconnect", {
    method: "POST",
    body: JSON.stringify({ forget }),
  });
}

/** Lời chào "đang dùng gói ChatGPT" chỉ hiện ở lần kết nối đầu tiên trên trình duyệt này. */
export function shouldWelcome(): boolean {
  try {
    return window.localStorage.getItem(WELCOME_KEY) !== "1";
  } catch {
    return false;
  }
}

export function markWelcomed() {
  try {
    window.localStorage.setItem(WELCOME_KEY, "1");
  } catch {
    // Bộ nhớ trình duyệt bị chặn: chỉ mất lời chào, không ảnh hưởng kết nối.
  }
}

export function providerLabel(id: string): string {
  return id === CHATGPT_PLAN_PROVIDER ? "Gói ChatGPT của tôi" : id;
}
