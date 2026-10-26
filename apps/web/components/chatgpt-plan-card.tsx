"use client";

import { useEffect, useState } from "react";
import {
  CHATGPT_USAGE_URL,
  type ChatGPTPlanStatus,
  disconnectChatGPTPlan,
  getChatGPTPlan,
  markWelcomed,
  shouldWelcome,
  startChatGPTPlan,
  updateChatGPTPlan,
} from "@/lib/chatgpt-plan";

type Notice = { type: "error" | "success"; text: string };

function errorText(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

/** Thẻ trong trang Tài khoản: người dùng tự nối gói ChatGPT Plus/Pro để dùng quota của chính họ. */
export function ChatGPTPlanCard({
  justConnected = false,
  navigate = (url: string) => window.location.assign(url),
}: {
  justConnected?: boolean;
  navigate?: (url: string) => void;
}) {
  const [plan, setPlan] = useState<ChatGPTPlanStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [welcome, setWelcome] = useState(false);

  useEffect(() => {
    let active = true;
    getChatGPTPlan()
      .then((value) => {
        if (!active) return;
        setPlan(value);
        setWelcome(justConnected && value.status === "active" && shouldWelcome());
      })
      .catch((reason) => active && setLoadError(errorText(reason, "Không tải được trạng thái kết nối ChatGPT.")));
    return () => {
      active = false;
    };
  }, [justConnected]);

  async function connect() {
    setBusy(true);
    setNotice(null);
    try {
      navigate(await startChatGPTPlan());
    } catch (reason) {
      setNotice({ type: "error", text: errorText(reason, "Không bắt đầu được kết nối ChatGPT.") });
      setBusy(false);
    }
  }

  async function save(preferences: { model?: string; use_by_default?: boolean }) {
    setBusy(true);
    setNotice(null);
    try {
      setPlan(await updateChatGPTPlan(preferences));
    } catch (reason) {
      setNotice({ type: "error", text: errorText(reason, "Không lưu được lựa chọn.") });
    } finally {
      setBusy(false);
    }
  }

  async function disconnect(forget: boolean) {
    if (forget && !window.confirm("Xóa hẳn kết nối? Lần sau bạn sẽ đăng ký lại từ đầu (dùng khi muốn đổi sang tài khoản ChatGPT khác).")) return;
    setBusy(true);
    setNotice(null);
    try {
      const result = await disconnectChatGPTPlan(forget);
      setPlan(result.connection);
      setNotice(result.remote_revoked
        ? { type: "success", text: "Đã ngắt kết nối và thu hồi quyền tại ChatGPT." }
        : { type: "error", text: "Đã xóa token trên hệ thống nhưng chưa xác nhận được việc thu hồi tại ChatGPT. Bạn có thể tự ngắt ứng dụng trong Cài đặt ChatGPT." });
    } catch (reason) {
      setNotice({ type: "error", text: errorText(reason, "Không ngắt được kết nối.") });
    } finally {
      setBusy(false);
    }
  }

  const usageUrl = plan?.usage_url ?? CHATGPT_USAGE_URL;
  const manageUsage = <a href={usageUrl} target="_blank" rel="noopener noreferrer">Quản lý mức dùng</a>;

  return (
    <section className="panel account-panel plan-card" aria-labelledby="chatgpt-plan-title" aria-busy={!plan && !loadError}>
      <div className="section-heading compact">
        <div>
          <h2 id="chatgpt-plan-title">Dùng gói ChatGPT của bạn</h2>
          <p className="muted">Việc AI bạn khởi chạy (gửi link, tài liệu, nghiên cứu sâu, chat) được tính vào hạn mức gói ChatGPT Plus/Pro của chính bạn thay vì khóa API của hệ thống.</p>
        </div>
      </div>
      {loadError && <p className="notice error-notice" role="alert">{loadError}</p>}
      {!plan && !loadError && <div aria-hidden="true"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-line short" /></div>}
      {plan && !plan.enabled && <p className="notice">Quản trị viên chưa bật tính năng này trên máy chủ.</p>}
      {plan?.enabled && welcome && (
        <div className="notice document-success plan-welcome" role="status">
          <strong>Bạn đang dùng gói ChatGPT của mình</strong>
          <p>Các việc AI đủ điều kiện trong ứng dụng sẽ dùng hạn mức gói ChatGPT của bạn. Bạn có thể đặt giới hạn riêng cho ứng dụng này trong cài đặt ChatGPT. {manageUsage}</p>
          <button type="button" className="secondary" onClick={() => { markWelcomed(); setWelcome(false); }}>Đã hiểu</button>
        </div>
      )}
      {plan?.enabled && plan.status === "active" && (
        <div className="plan-body">
          <p className="plan-state"><span className="badge plan-badge">Đang dùng gói ChatGPT</span>{plan.email && <span>{plan.email}</span>}{manageUsage}</p>
          {plan.last_error_code === "CHATGPT_PLAN_LIMIT_REACHED" && (
            <p className="notice error-notice" role="alert">Lần gần nhất đã chạm hạn mức gói ChatGPT hoặc giới hạn riêng của ứng dụng này. {manageUsage}</p>
          )}
          {plan.models.length > 0 && (
            <label className="inline-field">Model
              <select value={plan.model ?? ""} disabled={busy} onChange={(event) => save({ model: event.target.value })}>
                {plan.models.map((item) => <option key={item.slug} value={item.slug}>{item.display_name}</option>)}
              </select>
            </label>
          )}
          <label className="inline-field">
            <input type="checkbox" checked={plan.use_by_default} disabled={busy} onChange={(event) => save({ use_by_default: event.target.checked })} />
            Dùng mặc định cho việc AI mới của tôi
          </label>
          <div className="plan-actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => disconnect(false)}>Ngắt kết nối</button>
            <button type="button" className="secondary" disabled={busy} onClick={() => disconnect(true)}>Xóa kết nối</button>
          </div>
        </div>
      )}
      {plan?.enabled && plan.status !== "active" && (
        <div className="plan-body">
          {plan.status === "reauth_required" && <p className="notice error-notice" role="alert">Phiên ChatGPT đã hết hạn hoặc bị thu hồi. Hãy kết nối lại.</p>}
          {plan.status === "plan_disabled" && <p className="notice">Bạn đã đăng nhập ChatGPT nhưng chưa cho phép ứng dụng dùng gói của mình.</p>}
          {plan.mode === "local" && <p className="muted plan-hint">Chế độ cục bộ: hãy mở trang này trên chính máy đang chạy hệ thống, vì ChatGPT chỉ trả về địa chỉ 127.0.0.1.</p>}
          <div className="plan-actions">
            <button type="button" disabled={busy} onClick={connect}>{busy ? "Đang mở ChatGPT…" : plan.status === "plan_disabled" ? "Cho phép dùng gói ChatGPT" : "Tiếp tục với ChatGPT"}</button>
            {plan.status !== "not_connected" && <button type="button" className="secondary" disabled={busy} onClick={() => disconnect(true)}>Xóa kết nối</button>}
          </div>
        </div>
      )}
      {notice && <p className={`notice ${notice.type === "error" ? "error-notice" : "document-success"}`} role={notice.type === "error" ? "alert" : "status"}>{notice.text}</p>}
    </section>
  );
}
