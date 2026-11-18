"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, vietnameseApiErrorMessage } from "@/lib/api";
import { listLocalChatModels, verifyLocalChatModel, type LocalChatProvider, type LocalChatSelection } from "@/lib/chat";

type Props = {
  provider: LocalChatProvider;
  preferredModel?: string;
  disabled?: boolean;
  onVerifiedChange: (selection: LocalChatSelection | null) => void;
};

export function ChatLocalModelSettings(props: Props) {
  // A provider switch destroys the previous list, probe and in-flight identity.
  return <LocalModelSelection key={props.provider} {...props} />;
}

function LocalModelSelection({ provider, preferredModel, disabled = false, onVerifiedChange }: Props) {
  const [models, setModels] = useState<string[] | null>(null);
  const [model, setModel] = useState("");
  const [pending, setPending] = useState<"models" | "verify" | null>(null);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);

  useEffect(() => {
    onVerifiedChange(null);
    return () => { active.current?.abort(); active.current = null; };
  }, [onVerifiedChange]);

  function invalidate(clearModels: boolean) {
    active.current?.abort(); active.current = null;
    setPending(null); setError(null); setVerified(false);
    onVerifiedChange(null);
    if (clearModels) { setModels(null); setModel(""); }
  }

  function failure(caught: unknown): string {
    return caught instanceof ApiError ? vietnameseApiErrorMessage(caught.code, caught.status)
      : "Chưa thể kết nối với mô hình cục bộ. Hãy thử lại hoặc liên hệ quản trị viên.";
  }

  async function loadModels() {
    if (disabled || pending === "models") return;
    invalidate(true);
    const controller = new AbortController(); active.current = controller;
    setPending("models");
    try {
      const result = await listLocalChatModels(provider, controller.signal);
      if (active.current !== controller) return;
      if (result.provider !== provider || !Array.isArray(result.models)
        || result.models.some((name) => typeof name !== "string" || !name.trim())) {
        setError("Chưa nhận được danh sách mô hình hợp lệ. Hãy tải lại."); return;
      }
      setModels(result.models);
      setModel(preferredModel && result.models.includes(preferredModel) ? preferredModel : result.models[0] ?? "");
    } catch (caught) {
      if (active.current === controller) setError(failure(caught));
    } finally {
      if (active.current === controller) { active.current = null; setPending(null); }
    }
  }

  async function verify() {
    if (disabled || pending || !models?.includes(model)) return;
    invalidate(false);
    const controller = new AbortController(); active.current = controller;
    setPending("verify");
    try {
      const result = await verifyLocalChatModel(provider, model, controller.signal);
      if (active.current !== controller) return;
      if (result.verified !== true || result.provider !== provider || result.model_name !== model) {
        setError("Máy chủ chưa xác nhận đúng mô hình đã chọn. Hãy kiểm tra lại."); return;
      }
      setVerified(true);
      onVerifiedChange({ provider, model_name: model });
    } catch (caught) {
      if (active.current === controller) setError(failure(caught));
    } finally {
      if (active.current === controller) { active.current = null; setPending(null); }
    }
  }

  return <div className="chat-local-model-settings chat-new-form" aria-busy={Boolean(pending)}>
    <p>Mô hình chạy trên máy chủ hoặc máy được quản trị viên kết nối với hệ thống. Tải danh sách rồi kiểm tra mô hình bạn muốn dùng.</p>
    <button type="button" className="secondary" disabled={disabled || pending === "models"} onClick={() => void loadModels()}>
      {pending === "models" ? "Đang tải mô hình…" : models ? "Tải lại danh sách mô hình cục bộ" : "Tải danh sách mô hình cục bộ"}
    </button>
    <label>Mô hình cục bộ<select aria-label="Mô hình cục bộ" value={model} disabled={disabled || !models?.length} onChange={(event) => { invalidate(false); setModel(event.target.value); }}>
      {!model && <option value="">{models === null ? "Tải danh sách trước khi chọn" : "Chưa có mô hình để chọn"}</option>}
      {models?.map((name) => <option key={name} value={name}>{name}</option>)}
    </select></label>
    {models?.length === 0 && <p role="status" className="chat-api-notice">Chưa có mô hình nào sẵn sàng. Hãy nhờ quản trị viên mở mô hình đã cài rồi tải lại danh sách.</p>}
    {pending && <p role="status" className="chat-api-notice">{pending === "models" ? "Đang lấy danh sách mô hình…" : "Đang kiểm tra phản hồi của mô hình…"}</p>}
    {error && <p role="alert" className="chat-api-error">{error}</p>}
    {verified && <p role="status" className="chat-api-notice">Đã kiểm tra mô hình {model}. Bạn có thể tạo hoặc nhập cuộc trò chuyện.</p>}
    <small>Mô hình được giữ cố định theo cuộc trò chuyện. Bước kiểm tra gửi một câu thử ngắn, không kèm nội dung nghiên cứu.</small>
    <button type="button" className="secondary" disabled={disabled || Boolean(pending) || !models?.includes(model)} onClick={() => void verify()}>
      {pending === "verify" ? "Đang kiểm tra…" : verified ? "Kiểm tra lại mô hình cục bộ" : "Kiểm tra mô hình cục bộ"}
    </button>
  </div>;
}
