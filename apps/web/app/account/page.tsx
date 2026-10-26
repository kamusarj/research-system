"use client";

import { FormEvent, useEffect, useState } from "react";
import { ChatGPTPlanCard } from "@/components/chatgpt-plan-card";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { MIN_PASSWORD_LENGTH, changeOwnPassword } from "@/lib/members";

export default function AccountPage() {
  const { t } = useI18n();
  const { enabled, user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const [justConnected, setJustConnected] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("chatgpt") !== "connected") return;
    setJustConnected(true);
    window.history.replaceState(null, "", window.location.pathname);
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (next !== confirm) {
      setNotice({ type: "error", text: "Mật khẩu mới và phần nhập lại chưa khớp." });
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      await changeOwnPassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setNotice({ type: "success", text: "Đã đổi mật khẩu. Các phiên đăng nhập trên thiết bị khác đã được đăng xuất." });
    } catch (reason) {
      setNotice({ type: "error", text: reason instanceof Error ? reason.message : "Không thể đổi mật khẩu." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div><p className="eyebrow">Tài khoản</p><h1>{user?.name ?? "Tài khoản"}</h1>
          {user && <p className="page-description">{user.email} · {t(`role${user.role[0].toUpperCase()}${user.role.slice(1)}`)}</p>}
        </div>
      </header>
      <ChatGPTPlanCard justConnected={justConnected} />
      {!enabled ? (
        <p className="notice">Hệ thống đang chạy ở chế độ cục bộ không đăng nhập nên không có mật khẩu để đổi.</p>
      ) : (
        <section className="panel account-panel">
          <div className="section-heading compact"><div><h2>Đổi mật khẩu</h2><p className="muted">Tối thiểu {MIN_PASSWORD_LENGTH} ký tự. Nên đổi ngay sau lần đăng nhập đầu tiên bằng mật khẩu tạm.</p></div></div>
          <form className="form inset-form" onSubmit={submit}>
            <label>Mật khẩu hiện tại<input type="password" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} required /></label>
            <label>Mật khẩu mới<input type="password" autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} maxLength={128} value={next} onChange={(event) => setNext(event.target.value)} required /></label>
            <label>Nhập lại mật khẩu mới<input type="password" autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} maxLength={128} value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></label>
            {notice && <p className={`notice ${notice.type === "error" ? "error-notice" : "document-success"}`} role={notice.type === "error" ? "alert" : "status"}>{notice.text}</p>}
            <button disabled={busy}>{busy ? "Đang lưu…" : "Đổi mật khẩu"}</button>
          </form>
        </section>
      )}
    </>
  );
}
