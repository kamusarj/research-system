"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, vietnameseApiErrorMessage } from "@/lib/api";
import { listPersonalChatModels, verifyPersonalChatModel } from "@/lib/chat";

export type PersonalChatConnection = { apiKey: string; model: string; verifiedModels?: string[] };
export type PersonalChatConnections = Partial<Record<string, PersonalChatConnection>>;
export const personalChatProviders = ["openai", "deepseek"] as const;

export function ChatApiSettings({ initialProvider, models, pinnedModel, connections, onSave, onForget, onClose }: {
  initialProvider: string;
  models: Record<string, string>;
  pinnedModel?: string;
  connections: PersonalChatConnections;
  onSave: (provider: string, connection: PersonalChatConnection) => void;
  onForget: (provider: string) => void;
  onClose: () => void;
}) {
  const initial = personalChatProviders.includes(initialProvider as "openai" | "deepseek") ? initialProvider : "openai";
  const [provider, setProvider] = useState(initial);
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [visible, setVisible] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[] | null>(null);
  const [pending, setPending] = useState<"models" | "verify" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  // Abort and guard commits: a response may have resolved just before cancellation.
  useEffect(() => () => { active.current?.abort(); active.current = null; }, []);

  function invalidate(clearModels: boolean) {
    active.current?.abort(); active.current = null;
    setPending(null); setError(null);
    if (clearModels) { setAvailableModels(null); setModel(""); }
  }

  function failure(caught: unknown) {
    // Unknown/raw fetch errors may contain sensitive inputs; never render them.
    return caught instanceof ApiError ? vietnameseApiErrorMessage(caught.code, caught.status)
      : "Không thể kết nối với máy chủ. Hãy kiểm tra mạng rồi thử lại.";
  }

  async function loadModels() {
    if (pending) return;
    const key = apiKey.trim();
    invalidate(true);
    if (!/^[\x21-\x7e]{8,4096}$/.test(key)) {
      setError("API key chưa đúng định dạng. Hãy dán đầy đủ khóa, không kèm khoảng trắng hoặc xuống dòng.");
      return;
    }
    const controller = new AbortController(); active.current = controller;
    setPending("models");
    try {
      const result = await listPersonalChatModels(provider, key, controller.signal);
      if (active.current !== controller) return;
      setAvailableModels(result.models);
      const preferred = pinnedModel ?? connections[provider]?.model ?? models[provider];
      setModel(result.models.includes(preferred) ? preferred : pinnedModel ? "" : result.models[0] ?? "");
      if (pinnedModel && !result.models.includes(pinnedModel)) setError(`Khóa này không liệt kê mô hình ${pinnedModel} của cuộc trò chuyện. Hãy dùng khóa có quyền với mô hình này hoặc tạo cuộc trò chuyện mới.`);
    } catch (caught) {
      if (active.current === controller) setError(failure(caught));
    } finally {
      if (active.current === controller) { active.current = null; setPending(null); }
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || !availableModels?.includes(model) || !apiKey.trim()) return;
    const controller = new AbortController(); active.current = controller;
    setPending("verify"); setError(null);
    const key = apiKey.trim();
    try {
      const result = await verifyPersonalChatModel(provider, key, model, controller.signal);
      if (active.current !== controller) return;
      if (result.verified !== true || result.provider !== provider || result.model_name !== model) {
        setError("Máy chủ chưa xác nhận đúng mô hình đã chọn. Hãy kiểm tra lại."); return;
      }
      const previous = connections[provider];
      const verifiedModels = [...new Set([...(previous?.apiKey === key ? previous.verifiedModels ?? [] : []), model])];
      setApiKey("");
      onSave(provider, { apiKey: key, model, verifiedModels });
    } catch (caught) {
      if (active.current === controller) setError(failure(caught));
    } finally {
      if (active.current === controller) { active.current = null; setPending(null); }
    }
  }

  return <div className="chat-setup chat-api-settings">
    <div className="chat-setup-heading"><span className="chat-welcome-icon" aria-hidden="true">⌘</span><h2>Kết nối API của bạn</h2><p>Nhập khóa, chọn mô hình và kiểm tra kết nối. Phí sử dụng được tính trực tiếp trên tài khoản của bạn tại nhà cung cấp.</p></div>
    <form className="chat-new-form" onSubmit={submit} autoComplete="off" aria-busy={Boolean(pending)}>
      <label>Nhà cung cấp API<select value={provider} disabled={Boolean(pinnedModel)} onChange={(event) => { invalidate(true); setProvider(event.target.value); setApiKey(""); setVisible(false); }}>{personalChatProviders.map((id) => <option key={id} value={id}>{id === "openai" ? "OpenAI" : "DeepSeek"}</option>)}</select></label>
      <label htmlFor="personal-api-key">API key cá nhân</label>
      <div className="chat-api-key-field"><input id="personal-api-key" required type={visible ? "text" : "password"} value={apiKey} onChange={(event) => { invalidate(true); setApiKey(event.target.value); }} minLength={8} maxLength={4096} autoComplete="off" spellCheck={false} autoCapitalize="none" placeholder="Dán API key của bạn" /><button type="button" className="secondary" aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? "Ẩn khóa" : "Hiện khóa"}</button></div>
      <button type="button" className="secondary" disabled={Boolean(pending) || !apiKey.trim()} onClick={loadModels}>{pending === "models" ? "Đang tải mô hình…" : availableModels ? "Tải lại danh sách mô hình" : "Tải danh sách mô hình"}</button>
      <label>Mô hình AI<select value={model} disabled={!availableModels?.length || Boolean(pinnedModel)} onChange={(event) => { invalidate(false); setModel(event.target.value); }}>
        {!model && <option value="">{availableModels === null ? "Nhập khóa và tải danh sách trước" : "Chưa có mô hình để chọn"}</option>}
        {availableModels?.map((id) => <option key={id} value={id}>{id}</option>)}
      </select></label>
      {pinnedModel ? <small>Cuộc trò chuyện này dùng cố định {pinnedModel}. Muốn đổi mô hình, hãy tạo cuộc trò chuyện mới.</small> : <small>Danh sách do nhà cung cấp trả về, có thể gồm mô hình không hỗ trợ chat hoặc gọi công cụ. Bước kiểm tra sẽ xác nhận mô hình bạn chọn.</small>}
      {availableModels?.length === 0 && <p role="status" className="chat-api-notice">API không trả về mô hình nào. Hãy kiểm tra quyền của khóa/dự án rồi tải lại danh sách.</p>}
      {pending && <p role="status" className="chat-api-notice">{pending === "models" ? "Đang xác thực khóa và lấy danh sách mô hình…" : "Đang kiểm tra quyền dùng mô hình và khả năng thực hiện yêu cầu…"}</p>}
      {error && <p role="alert" className="chat-api-error">{error}</p>}
      <p className="chat-api-retention">Khóa chỉ được giữ tạm trong trang và gửi qua máy chủ để gọi nhà cung cấp; không lưu vào lịch sử, cơ sở dữ liệu hay bộ nhớ trình duyệt. Tải lại, rời trang hoặc đăng xuất sẽ xóa khóa. Lịch sử chat vẫn thuộc kho chung của nhóm.</p>
      <small>Bấm kiểm tra sẽ gửi một yêu cầu thử, tối đa 16 token đầu ra và có thể phát sinh phí nhỏ. Không gửi nội dung nghiên cứu. Thành công chỉ xác nhận tại thời điểm kiểm tra, không đảm bảo số dư lâu dài.</small>
      <button disabled={Boolean(pending) || !availableModels?.includes(model) || !apiKey.trim()}>{pending === "verify" ? "Đang kiểm tra…" : "Kiểm tra và kết nối"}</button>
    </form>
    {Object.entries(connections).map(([id]) => <div className="chat-api-saved" key={id}><span>{id === "openai" ? "OpenAI" : "DeepSeek"} · Đã kiểm tra cho trang này</span><button className="secondary" onClick={() => { invalidate(true); onForget(id); setApiKey(""); }}>Xóa khóa {id === "openai" ? "OpenAI" : "DeepSeek"}</button></div>)}
    <button className="secondary chat-setup-cancel" onClick={() => { invalidate(true); setApiKey(""); onClose(); }}>Quay lại trò chuyện</button>
  </div>;
}
