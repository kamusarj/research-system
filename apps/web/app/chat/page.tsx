"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  SelectionActionPopover,
  selectionAnchorFromRect,
  type SelectionAnchor,
} from "@/components/selection-action-popover";
import { StatusBadge } from "@/components/status-badge";
import { ChatMarkdown, ChatMedia } from "@/components/chat-markdown";
import { ChatApiSettings, type PersonalChatConnections } from "@/components/chat-api-settings";
import { api, vietnameseApiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  closeChatSession,
  createChatSession,
  importChatGPTSharedChat,
  listChatMessages,
  listChatSessions,
  sendChatMessage,
} from "@/lib/chat";
import { useI18n } from "@/lib/i18n";
import type { ChatScopeType, Provider } from "@/lib/types";

const scopeTypes: ChatScopeType[] = ["graph", "pillar", "node", "document", "change_set", "gap"];
const CHAT_SELECTION_MAX_CHARS = 6000;
// AI hệ thống cho chat: API trả phí cùng các CLI dùng gói đăng nhập trên máy chủ.
const systemChatProviders = ["deepseek", "openai", "claude_code", "codex", "antigravity"];

const starters = [
  { icon: "✧", title: "Phát triển ý tưởng", description: "Từ ý tưởng ban đầu đến hướng triển khai", prompt: "Tôi muốn phát triển một ý tưởng về tác nhân AI cho doanh nghiệp. Hãy giúp tôi làm rõ vấn đề, đối tượng sử dụng và cách kiểm chứng ý tưởng." },
  { icon: "◎", title: "Kết nối kiến thức", description: "Tìm mối liên hệ trong kho tri thức", prompt: "Dựa trên phạm vi tri thức hiện tại, hãy chỉ ra những khái niệm có liên quan và giải thích mối liên hệ giữa chúng. Nêu rõ nguồn và phần chưa đủ bằng chứng." },
  { icon: "↗", title: "Tìm hướng nghiên cứu", description: "Nhận diện câu hỏi còn bỏ ngỏ", prompt: "Trong phạm vi tri thức hiện tại, những câu hỏi nào còn thiếu bằng chứng? Hãy đề xuất ba hướng nghiên cứu tiếp theo và cách kiểm chứng từng hướng." },
];

function chatFailure(code: string): string {
  if (code === "CHAT_PROVIDER_UNAVAILABLE") return "Chưa thể kết nối với AI của cuộc trò chuyện này. Hãy kiểm tra cấu hình nhà cung cấp hoặc tạo cuộc trò chuyện mới với AI đã được cấu hình.";
  if (code.includes("TIMEOUT")) return "AI phản hồi lâu hơn dự kiến. Bạn có thể gửi lại câu hỏi ngắn hơn sau ít phút.";
  if (code.includes("RATE_LIMIT")) return "AI đang giới hạn số lượt yêu cầu. Hãy đợi một chút trước khi gửi lại.";
  if (code.startsWith("CHAT_")) return vietnameseApiErrorMessage(code);
  return "AI chưa thể trả lời yêu cầu này. Hãy thử diễn đạt lại câu hỏi hoặc quay lại sau ít phút.";
}

type ChatSelection = {
  messageId: string;
  text: string;
  anchor: SelectionAnchor;
};

function markdownQuote(value: string): string {
  return value.split("\n").map((line) => `> ${line}`).join("\n");
}

export default function ChatPage() {
  const { user } = useAuth();
  // Remount on identity changes so no personal key survives account switching.
  return <ChatWorkspace key={user?.id ?? "anonymous"} />;
}

function ChatWorkspace() {
  const { t } = useI18n();
  const { can } = useAuth();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showApi, setShowApi] = useState(false);
  const [apiProvider, setApiProvider] = useState("openai");
  const [connections, setConnections] = useState<PersonalChatConnections>({});
  const [credentialSource, setCredentialSource] = useState<"system" | "personal">("system");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [importUrl, setImportUrl] = useState("");
  const [title, setTitle] = useState("");
  const [scopeType, setScopeType] = useState<ChatScopeType>("graph");
  const [scopeId, setScopeId] = useState("");
  const [provider, setProvider] = useState("");
  const [draft, setDraft] = useState("");
  const [chatSelection, setChatSelection] = useState<ChatSelection | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const sessions = useQuery({ queryKey: ["chat-sessions"], queryFn: listChatSessions });
  const providers = useQuery({
    queryKey: ["ai-providers"],
    queryFn: () => api<Provider[]>("/ai/providers"),
  });
  const messages = useQuery({
    queryKey: ["chat-messages", selectedId],
    queryFn: () => listChatMessages(selectedId!),
    enabled: Boolean(selectedId),
  });

  useEffect(() => {
    if (!selectedId && sessions.data?.items.length) setSelectedId(sessions.data.items[0].id);
  }, [selectedId, sessions.data]);

  useEffect(() => setChatSelection(null), [selectedId]);

  useEffect(() => {
    const list = messageListRef.current;
    if (list) list.scrollTop = messages.data?.length ? list.scrollHeight : 0;
  }, [selectedId, messages.data?.length, working]);

  useEffect(() => {
    const input = composerRef.current;
    if (input) {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
    }
  }, [draft, selectedId, showNew, showImport]);

  useEffect(() => {
    const parameters = new URLSearchParams(window.location.search);
    const requestedScope = parameters.get("scope_type") as ChatScopeType | null;
    const requestedId = parameters.get("scope_id");
    if (requestedScope && scopeTypes.includes(requestedScope)) {
      setScopeType(requestedScope);
      setScopeId(requestedId ?? "");
      setShowNew(true);
    }
  }, []);

  const selected = sessions.data?.items.find((item) => item.id === selectedId) ?? null;
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLocaleLowerCase("vi");
  const filteredSessions = (sessions.data?.items ?? []).filter((item) => normalize(item.title).includes(normalize(search.trim())));
  function openNewChat() {
    setShowApi(false);
    setShowNew(true);
    setShowImport(false);
    setHistoryOpen(false);
    setError(null);
  }
  function prepareStarter(prompt: string) {
    setDraft(prompt);
    if (!selected || selected.status !== "active" || !selectedConnectionReady) openNewChat();
    else window.requestAnimationFrame(() => composerRef.current?.focus());
  }
  const chatProviders = useMemo(
    () => (providers.data ?? []).filter((item) => systemChatProviders.includes(item.id)),
    [providers.data],
  );
  const configuredChatProviders = useMemo(() => chatProviders.filter((item) => item.configured), [chatProviders]);
  const connectionOptions = useMemo(() => credentialSource === "personal"
    ? Object.entries(connections).flatMap(([id, value]) => value ? [{ id, model: value.model, chat_active: false }] : [])
    : configuredChatProviders, [credentialSource, connections, configuredChatProviders]);
  const selectedProvider = selected
    ? chatProviders.find((item) => item.id === selected.provider_name)
    : null;
  const selectedPersonalKey = selected?.credential_source === "personal" ? connections[selected.provider_name]?.apiKey : undefined;
  const selectedConnectionReady = selected?.credential_source === "personal"
    ? Boolean(selectedPersonalKey && connections[selected.provider_name]?.verifiedModels?.includes(selected.model_name))
    : Boolean(selectedProvider?.configured);
  function openApiSettings(providerName = selected?.provider_name ?? provider) {
    setApiProvider(providerName || "openai");
    setShowApi(true);
    setHistoryOpen(false);
    setError(null);
    setChatSelection(null);
  }
  function connectionRequest() {
    if (credentialSource === "system") return {};
    const connection = connections[provider];
    if (!connection) throw new Error("Hãy nhập API key cá nhân trước khi tạo cuộc trò chuyện.");
    return { credential_source: "personal" as const, model_name: connection.model, personal_api_key: connection.apiKey };
  }
  useEffect(() => {
    if (provider && connectionOptions.some((item) => item.id === provider)) return;
    const preferred = connectionOptions.find((item) => item.chat_active) ?? connectionOptions[0];
    setProvider(preferred?.id ?? "");
  }, [connectionOptions, provider]);
  function captureChatSelection(messageId: string, container: HTMLElement) {
    const selection = window.getSelection();
    if (
      !selection
      || selection.isCollapsed
      || selection.rangeCount === 0
      || !selection.anchorNode
      || !selection.focusNode
      || !container.contains(selection.anchorNode)
      || !container.contains(selection.focusNode)
    ) {
      setChatSelection(null);
      return;
    }
    const text = selection.toString().trim().slice(0, CHAT_SELECTION_MAX_CHARS);
    if (!text) {
      setChatSelection(null);
      return;
    }
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const fallback = container.getBoundingClientRect();
    setChatSelection({
      messageId,
      text,
      anchor: selectionAnchorFromRect(rect.width || rect.height ? rect : fallback),
    });
  }

  function prepareSelectedChat(action: "ask" | "explain" | "summarize") {
    if (!chatSelection) return;
    const key = action === "ask"
      ? "askAboutSelectionPrompt"
      : action === "explain"
        ? "explainSelectionPrompt"
        : "summarizeSelectionPrompt";
    const prepared = `${t(key)}\n\n${markdownQuote(chatSelection.text)}`;
    setDraft((current) => `${current.trim() ? `${current.trim()}\n\n` : ""}${prepared}`.slice(0, 12000));
    setChatSelection(null);
    if (selected?.status !== "active") {
      setShowNew(true);
      setShowImport(false);
      return;
    }
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  async function createSession(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    try {
      const created = await createChatSession({
        title: title.trim() || undefined,
        scope_type: scopeType,
        scope_id: scopeType === "graph" ? undefined : scopeId.trim(),
        provider,
        ...connectionRequest(),
      });
      await sessions.refetch();
      setSelectedId(created.id);
      setTitle("");
      setScopeId("");
      setShowNew(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setWorking(false);
    }
  }

  async function importSharedChat(event: FormEvent) {
    event.preventDefault();
    if (!importUrl.trim()) return;
    setWorking(true);
    setError(null);
    try {
      const imported = await importChatGPTSharedChat({
        url: importUrl.trim(),
        provider,
        ...connectionRequest(),
      });
      await sessions.refetch();
      setSelectedId(imported.id);
      setImportUrl("");
      setShowImport(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setWorking(false);
    }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !draft.trim() || working || selected?.status !== "active" || !selectedConnectionReady) return;
    const content = draft.trim();
    setWorking(true);
    setError(null);
    setDraft("");
    try {
      if (selected.credential_source === "personal") await sendChatMessage(selectedId, content, selectedPersonalKey);
      else await sendChatMessage(selectedId, content);
      await Promise.all([messages.refetch(), sessions.refetch()]);
    } catch (reason) {
      setDraft(content);
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
      await messages.refetch();
    } finally {
      setWorking(false);
    }
  }

  async function closeSession() {
    if (!selectedId) return;
    setWorking(true);
    setError(null);
    try {
      await closeChatSession(selectedId);
      await sessions.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <header className="page-header chat-page-header">
        <div><span className="chat-eyebrow">CÙNG SUY NGHĨ, HIỂU SÂU HƠN</span><h1>Trò chuyện với AI</h1><p>Mở rộng ý tưởng từ tri thức của bạn.</p></div>
        {can("researcher") && <div className="actions">
          <button className="secondary" disabled={working} onClick={() => openApiSettings()}>API của tôi</button>
          <button className="secondary" disabled={working} onClick={() => { setShowApi(false); setShowImport(true); setShowNew(false); setHistoryOpen(false); setError(null); }}>{t("importChatGPT")}</button>
          <button disabled={working} onClick={openNewChat}><span aria-hidden="true">＋ </span>{t("newChat")}</button>
        </div>}
      </header>
      {error && <p role="alert" className="notice error-notice">{error}</p>}
      {!providers.isLoading && configuredChatProviders.length === 0 && !Object.keys(connections).length && !showApi && (
        <p className="notice graph-warning">Chưa có AI được thiết lập. {can("researcher") && <button className="secondary" onClick={() => openApiSettings()}>Nhập API của bạn</button>}</p>
      )}

      <button className="secondary chat-history-toggle" aria-expanded={historyOpen} aria-controls="chat-history" onClick={() => setHistoryOpen(!historyOpen)}>{historyOpen ? "Ẩn lịch sử" : "Lịch sử trò chuyện"}<span>{sessions.data?.total ?? 0}</span></button>
      <div className={`chat-workspace ${historyOpen ? "history-open" : ""}`}>
        <aside id="chat-history" className="chat-sidebar card" aria-label="Lịch sử trò chuyện">
          <div className="panel-heading"><h2>Lịch sử trò chuyện</h2><span>{sessions.data?.total ?? 0}</span></div>
          <label className="chat-history-search"><span className="sr-only">Tìm cuộc trò chuyện</span><input type="search" placeholder="Tìm cuộc trò chuyện…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <div className="chat-session-list">
            {sessions.isLoading && <p className="muted" role="status">Đang tải lịch sử…</p>}
            {sessions.isError && <p role="alert">Không thể tải lịch sử. <button className="secondary" onClick={() => sessions.refetch()}>Tải lại</button></p>}
            {filteredSessions.map((item) => (
              <button disabled={working} aria-current={selectedId === item.id ? "true" : undefined} className={selectedId === item.id ? "active" : ""} key={item.id} title={item.title} onClick={() => { setSelectedId(item.id); setShowApi(false); setShowNew(false); setShowImport(false); setHistoryOpen(false); setError(null); }}>
                <strong>{item.title}</strong>
                <span>{t(`chatScope.${item.scope_type}`)} · {item.message_count} {t("messages")}</span>
                <small>{item.source_type === "chatgpt_shared" ? "Từ ChatGPT · " : ""}{item.status === "closed" ? "Đã kết thúc · " : ""}{new Date(item.updated_at).toLocaleDateString("vi-VN", { day: "numeric", month: "short" })}</small>
              </button>
            ))}
            {!sessions.isLoading && !sessions.isError && !filteredSessions.length && <p className="muted">{search ? "Không tìm thấy cuộc trò chuyện phù hợp." : t("noChatSessions")}</p>}
          </div>
          <div className="chat-history-foot"><span aria-hidden="true">◷</span><div><strong>Tiếp nối mạch suy nghĩ</strong><p>Lịch sử được lưu trong hệ thống của bạn.</p></div></div>
        </aside>

        <section className="chat-thread card" aria-label="Không gian trò chuyện">
          {showApi && can("researcher") && <ChatApiSettings initialProvider={apiProvider} pinnedModel={!showNew && !showImport && selected?.credential_source === "personal" ? selected.model_name : undefined} models={Object.fromEntries(chatProviders.map((item) => [item.id, item.model]))} connections={connections} onSave={(id, connection) => { setConnections((current) => ({ ...current, [id]: connection })); setCredentialSource("personal"); setProvider(id); setShowApi(false); if (!showNew && !showImport && selected?.credential_source !== "personal") openNewChat(); }} onForget={(id) => setConnections((current) => { const next = { ...current }; delete next[id]; return next; })} onClose={() => setShowApi(false)} />}
          {!showApi && (showNew || showImport) && <div className="chat-setup">
            <div className="chat-setup-heading"><span className="chat-welcome-icon" aria-hidden="true">✦</span><h2>{showImport ? "Tiếp tục từ ChatGPT" : "Bắt đầu một mạch suy nghĩ mới"}</h2><p>{showImport ? "Mang cuộc trò chuyện đã chia sẻ vào không gian nghiên cứu của bạn." : "Chọn phạm vi kiến thức và AI đồng hành. Bạn có thể đặt tên để dễ tìm lại."}</p></div>
          {can("researcher") && showNew && (
            <form className="chat-new-form" onSubmit={createSession}>
              <label>{t("title")}<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder={t("optionalTitle")} /></label>
              <label>{t("chatScope")}<select value={scopeType} onChange={(event) => setScopeType(event.target.value as ChatScopeType)}>{scopeTypes.map((value) => <option value={value} key={value}>{t(`chatScope.${value}`)}</option>)}</select></label>
              <label>Nguồn API<select value={credentialSource} onChange={(event) => setCredentialSource(event.target.value as "system" | "personal")}><option value="system">API của hệ thống</option><option value="personal">API cá nhân của tôi</option></select></label>
              <label>{t("provider")}<select required value={provider} onChange={(event) => setProvider(event.target.value)}>{!connectionOptions.length && <option value="">Chưa có kết nối</option>}{connectionOptions.map((item) => <option value={item.id} key={item.id}>{item.id} · {item.model}</option>)}</select></label>
              {credentialSource === "personal" && <button type="button" className="secondary" onClick={() => openApiSettings(provider)}>Thiết lập API cá nhân</button>}
              {scopeType !== "graph" && <label>{t("scopeId")}<input required value={scopeId} onChange={(event) => setScopeId(event.target.value)} placeholder={t("scopeIdHint")} /></label>}
              <button disabled={working || !provider}>{t("createChat")}</button>
            </form>
          )}
          {can("researcher") && showImport && (
            <form className="chat-new-form chat-import-form" onSubmit={importSharedChat}>
              <p>{t("chatGPTImportHint")}</p>
              <label>{t("chatGPTSharedLink")}<input type="url" required value={importUrl} onChange={(event) => setImportUrl(event.target.value)} placeholder="https://chatgpt.com/share/…" /></label>
              <label>Nguồn API<select value={credentialSource} onChange={(event) => setCredentialSource(event.target.value as "system" | "personal")}><option value="system">API của hệ thống</option><option value="personal">API cá nhân của tôi</option></select></label>
              <label>{t("provider")}<select required value={provider} onChange={(event) => setProvider(event.target.value)}>{!connectionOptions.length && <option value="">Chưa có kết nối</option>}{connectionOptions.map((item) => <option value={item.id} key={item.id}>{item.id} · {item.model}</option>)}</select></label>
              {credentialSource === "personal" && <button type="button" className="secondary" onClick={() => openApiSettings(provider)}>Thiết lập API cá nhân</button>}
              <small>{t("chatGPTImportLocalOnly")}</small>
              <button disabled={working || !provider || !importUrl.trim()}>{working ? t("importingChat") : t("importChat")}</button>
            </form>
          )}
          <button className="secondary chat-setup-cancel" disabled={working} onClick={() => { setShowNew(false); setShowImport(false); }}>Quay lại trò chuyện</button>
          </div>}
          {!showApi && !showNew && !showImport && (selected ? (
            <>
              <header>
                <div className="chat-thread-heading">
                  <h2>{selected.title}</h2>
                  <div className="chat-thread-meta">
                    <span>Ngữ cảnh: {t(`chatScope.${selected.scope_type}`)}</span>
                    <span className="chat-provider-name">{selected.provider_name}</span>
                    {selected.credential_source === "personal" && <span className="chat-personal-badge">API cá nhân · {selected.model_name}</span>}
                    <StatusBadge status={selected.status} />
                    {selected.source_type === "chatgpt_shared" && selected.source_url && (
                      <a href={selected.source_url} target="_blank" rel="noreferrer">
                        {t("chatGPTSnapshot")}
                      </a>
                    )}
                  </div>
                </div>
                {can("researcher") && selected.status === "active" && (
                  <button className="secondary chat-close-button" disabled={working} onClick={closeSession}>
                    Kết thúc
                  </button>
                )}
              </header>
              <div className="chat-message-list" ref={messageListRef} role="log" aria-label="Nội dung hội thoại" aria-live="polite">
                {messages.isLoading && <p className="chat-thinking" role="status">Đang tải cuộc trò chuyện…</p>}
                {messages.isError && <p role="alert">Không thể tải tin nhắn. <button className="secondary" onClick={() => messages.refetch()}>Tải lại</button></p>}
                {(messages.data ?? []).map((message) => (
                  <article className={`chat-message ${message.role} ${message.origin_type === "chatgpt_shared" ? "imported" : ""} ${message.error_code ? "failed" : ""}`} key={message.id}>
                    <div className="chat-avatar" aria-hidden="true">{message.role === "user" ? "B" : "✦"}</div>
                    <div
                      className="chat-message-content"
                      data-chat-message-id={message.id}
                      onMouseUp={(event) => captureChatSelection(message.id, event.currentTarget)}
                    >
                      <strong>{message.role === "user" ? t("you") : "Trợ lý nghiên cứu"}<time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</time></strong>
                      {message.origin_type === "chatgpt_shared" && <span className="chat-origin-label">{t("importedSnapshotMessage")}</span>}
                      {message.error_code ? <div className="chat-failure"><h3>Chưa thể hoàn tất câu trả lời</h3><p>{chatFailure(message.error_code)}</p><details><summary>Chi tiết lỗi</summary><code>{message.error_code}</code></details>{can("researcher") && message.error_code === "CHAT_PROVIDER_UNAVAILABLE" && <button className="secondary" onClick={openNewChat}>Chọn AI cho cuộc trò chuyện mới</button>}</div> : <ChatMarkdown content={message.content} />}
                      <ChatMedia media={message.media} />
                      {message.linked_change_set_id && <Link href={`/graph/changes/${message.linked_change_set_id}`}>{t("reviewKnowledgeChanges")} →</Link>}
                    </div>
                  </article>
                ))}
                {working && <div className="chat-thinking"><span className="spinner" />{t("chatThinking")}</div>}
                {!messages.isLoading && !messages.isError && messages.data?.length === 0 && <div className="chat-empty"><span>✦</span><div className="chat-eyebrow">KHÔNG GIAN CHO Ý TƯỞNG CỦA BẠN</div><h2>Hôm nay, bạn muốn khám phá điều gì?</h2><p>Đặt câu hỏi, kết nối kiến thức hoặc cùng AI phát triển một hướng nghiên cứu mới.</p><div className="chat-starters">{starters.map((starter) => <button className="secondary" key={starter.title} disabled={!can("researcher") || working} onClick={() => prepareStarter(starter.prompt)}><span aria-hidden="true">{starter.icon}</span><strong>{starter.title}</strong><small>{starter.description}</small><b aria-hidden="true">↗</b></button>)}</div></div>}
              </div>
              {can("researcher") && <form className="chat-composer" onSubmit={send}>
                <label className="sr-only" htmlFor="chat-message">{t("chatMessage")}</label>
                {selected.status !== "active" ? <p className="chat-composer-status">Cuộc trò chuyện đã kết thúc. <button type="button" className="secondary" onClick={openNewChat}>Bắt đầu cuộc trò chuyện mới</button></p> : !selectedConnectionReady && !providers.isLoading && <p className="chat-composer-status">{selected.credential_source === "personal" ? "Nhập lại API key của bạn để tiếp tục. Hệ thống không lưu khóa cá nhân." : "AI của cuộc trò chuyện này chưa được cấu hình."} <button type="button" className="secondary" onClick={() => selected.credential_source === "personal" ? openApiSettings(selected.provider_name) : openNewChat()}>{selected.credential_source === "personal" ? "Nhập lại API key" : "Chọn AI khác"}</button></p>}
                <textarea ref={composerRef} id="chat-message" rows={2} value={draft} disabled={selected.status !== "active" || working || !selectedConnectionReady} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Hỏi một câu, chia sẻ ý tưởng hoặc yêu cầu phân tích…" maxLength={12000} />
                <div>
                  <span className="chat-keyboard-hint">Enter để gửi · Shift + Enter xuống dòng</span><span className="chat-character-count">{draft.length.toLocaleString("vi-VN")} / 12.000</span>
                  <button disabled={!draft.trim() || selected.status !== "active" || working || !selectedConnectionReady}>{t("sendMessage")} <span aria-hidden="true">↑</span></button>
                </div>
                <p className="chat-composer-note">AI có thể nhầm lẫn. Hãy kiểm tra nguồn; đề xuất tri thức cần bạn duyệt.</p>
              </form>}
            </>
          ) : <div className="chat-empty"><span>✦</span><div className="chat-eyebrow">TRỢ LÝ NGHIÊN CỨU CỦA BẠN</div><h2>Từ một câu hỏi, mở ra ý tưởng mới.</h2><p>Cùng AI phân tích, tìm mối liên hệ và khám phá những điều còn bỏ ngỏ trong kho tri thức.</p><div className="chat-starters">{starters.map((starter) => <button className="secondary" key={starter.title} disabled={!can("researcher")} onClick={() => prepareStarter(starter.prompt)}><span aria-hidden="true">{starter.icon}</span><strong>{starter.title}</strong><small>{starter.description}</small><b aria-hidden="true">↗</b></button>)}</div><p className="chat-welcome-note">Chọn một gợi ý để bắt đầu, hoặc mở lại cuộc trò chuyện từ lịch sử.</p></div>)}
        </section>
      </div>

      {chatSelection && can("researcher") && (
        <SelectionActionPopover
          anchor={chatSelection.anchor}
          label={t("chatSelectionActions")}
          onDismiss={() => setChatSelection(null)}
        >
          <button type="button" className="primary" onClick={() => prepareSelectedChat("ask")}>
            ✦ {t("askAiAboutSelection")}
          </button>
          <button type="button" onClick={() => prepareSelectedChat("explain")}>
            {t("explainSelection")}
          </button>
          <button type="button" onClick={() => prepareSelectedChat("summarize")}>
            {t("summarizeSelection")}
          </button>
        </SelectionActionPopover>
      )}
    </>
  );
}
