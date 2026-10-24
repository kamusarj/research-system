"use client";

import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import { type AuthUser, type Role, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import {
  MIN_PASSWORD_LENGTH,
  createMember,
  generateTemporaryPassword,
  listMembers,
  updateMember,
} from "@/lib/members";

const roles: Role[] = ["researcher", "viewer", "owner"];

function roleLabelKey(role: Role) {
  return `role${role[0].toUpperCase()}${role.slice(1)}`;
}

function errorText(reason: unknown, conflict: string): string {
  if (reason instanceof ApiError && reason.status === 409) return conflict;
  return reason instanceof Error ? reason.message : "Không thể hoàn tất yêu cầu.";
}

export default function MembersPage() {
  const { t } = useI18n();
  const { can, enabled, user, loading } = useAuth();
  const isOwner = can("owner");
  // Chỉ tải danh sách khi đã biết chắc vai trò, tránh một yêu cầu 403 trong lúc kiểm tra phiên.
  const members = useQuery({ queryKey: ["members"], queryFn: listMembers, enabled: isOwner && !loading });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("researcher");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: "error" | "success"; text: string } | null>(null);

  if (!isOwner) {
    return (
      <>
        <header className="page-header"><div><p className="eyebrow">Quản trị</p><h1>Thành viên nhóm</h1></div></header>
        <p className="notice">Chỉ chủ sở hữu được quản lý thành viên. Liên hệ chủ sở hữu nếu bạn cần đổi quyền.</p>
      </>
    );
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy("create");
    setNotice(null);
    try {
      const created = await createMember({ name: name.trim(), email: email.trim(), role, password });
      setNotice({
        type: "success",
        text: `Đã tạo tài khoản cho ${created.name} (${created.email}). Gửi email và mật khẩu tạm qua kênh riêng; thành viên tự đổi mật khẩu ở trang Tài khoản sau khi đăng nhập.`,
      });
      setName("");
      setEmail("");
      setRole("researcher");
      await members.refetch();
    } catch (reason) {
      setNotice({ type: "error", text: errorText(reason, "Email này đã có tài khoản.") });
    } finally {
      setBusy(null);
    }
  }

  async function change(member: AuthUser, data: Parameters<typeof updateMember>[1], success: string) {
    setBusy(member.id);
    setNotice(null);
    try {
      await updateMember(member.id, data);
      setNotice({ type: "success", text: success });
      await members.refetch();
    } catch (reason) {
      setNotice({
        type: "error",
        text: errorText(reason, "Không thể hạ quyền hoặc khóa chủ sở hữu cuối cùng, hoặc chính tài khoản đang đăng nhập."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function resetPassword(member: AuthUser) {
    if (!window.confirm(`Đặt mật khẩu tạm mới cho ${member.name}? Mọi phiên đăng nhập của người này sẽ bị đăng xuất.`)) return;
    const temporary = generateTemporaryPassword();
    await change(
      member,
      { password: temporary },
      `Mật khẩu tạm mới của ${member.email}: ${temporary} — chỉ hiển thị một lần, hãy gửi qua kênh riêng.`,
    );
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Quản trị</p>
          <h1>Thành viên nhóm</h1>
          <p className="page-description">
            Tạo tài khoản cho thành viên và phân quyền: nhà nghiên cứu gửi nguồn, soạn tài liệu và đề xuất thay đổi; người xem chỉ đọc; chủ sở hữu duyệt, xuất bản và quản trị.
          </p>
        </div>
      </header>
      {!enabled && (
        <p className="notice">
          Hệ thống đang chạy ở chế độ cục bộ không đăng nhập (AUTH_MODE=disabled). Tài khoản tạo ở đây sẽ dùng được khi bật bản triển khai nhóm.
        </p>
      )}
      {notice && (
        <p className={`notice ${notice.type === "error" ? "error-notice" : "document-success"}`} role={notice.type === "error" ? "alert" : "status"}>
          {notice.text}
        </p>
      )}
      <div className="split workspace-split members-layout">
        <section className="panel">
          <div className="section-heading compact"><div><h2>Thêm thành viên</h2><p className="muted">Mật khẩu tạm tối thiểu {MIN_PASSWORD_LENGTH} ký tự.</p></div></div>
          <form className="form inset-form" onSubmit={create}>
            <label>Họ tên<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={200} /></label>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="off" /></label>
            <label>Vai trò
              <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
                {roles.map((item) => <option key={item} value={item}>{t(roleLabelKey(item))}</option>)}
              </select>
            </label>
            <label>Mật khẩu tạm
              <span className="password-row">
                <input value={password} onChange={(event) => setPassword(event.target.value)} required minLength={MIN_PASSWORD_LENGTH} maxLength={128} autoComplete="new-password" />
                <button type="button" className="secondary" onClick={() => setPassword(generateTemporaryPassword())}>Tạo ngẫu nhiên</button>
              </span>
            </label>
            <button disabled={busy === "create"}>{busy === "create" ? "Đang tạo…" : "Tạo tài khoản"}</button>
          </form>
        </section>
        <section className="panel">
          <div className="section-heading compact"><div><h2>Danh sách tài khoản</h2></div><span>{members.data?.length ?? 0}</span></div>
          {members.error && <p className="notice error-notice">{members.error.message}</p>}
          <div className="stack">
            {members.data?.map((member) => {
              const self = member.id === user?.id;
              return (
                <article className="card compact-card member-card" key={member.id}>
                  <div className="list-item-head">
                    <div>
                      <h3>{member.name}{self && <span className="badge">Bạn</span>}</h3>
                      <p className="muted">{member.email}</p>
                    </div>
                    <span className={`badge ${member.active ? "" : "muted"}`}>{member.active ? "Đang hoạt động" : "Đã khóa"}</span>
                  </div>
                  <div className="actions member-actions">
                    <label className="inline-field">Vai trò
                      <select
                        aria-label={`Vai trò của ${member.name}`}
                        value={member.role}
                        disabled={self || busy === member.id}
                        onChange={(event) => void change(member, { role: event.target.value as Role }, `Đã đổi vai trò của ${member.name}.`)}
                      >
                        {roles.map((item) => <option key={item} value={item}>{t(roleLabelKey(item))}</option>)}
                      </select>
                    </label>
                    <button type="button" className="secondary" disabled={busy === member.id} onClick={() => void resetPassword(member)}>Đặt lại mật khẩu</button>
                    {!self && (
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy === member.id}
                        onClick={() => void change(
                          member,
                          { active: !member.active },
                          member.active ? `Đã khóa ${member.name} và đăng xuất mọi phiên.` : `Đã mở khóa ${member.name}.`,
                        )}
                      >
                        {member.active ? "Khóa tài khoản" : "Mở khóa"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
            {members.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
            {!members.isLoading && members.data?.length === 0 && <div className="table-state"><strong>Chưa có tài khoản nào.</strong></div>}
          </div>
        </section>
      </div>
    </>
  );
}
