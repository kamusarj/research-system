import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import ChatPage from "./chat-workspace";
import { createChatSession, importChatGPTSharedChat, sendChatMessage } from "@/lib/chat";
import type { ChatMessage, ChatSession } from "@/lib/types";

const session: ChatSession = {
  id: "session-1",
  title: "Agent governance",
  scope_type: "graph",
  scope_id: null,
  provider_name: "deepseek",
  model_name: "deepseek-test",
  conversation_summary: "",
  status: "active",
  prompt_version: "graph-chat-v1",
  source_type: "local",
  source_url: null,
  source_snapshot_hash: null,
  source_imported_at: null,
  imported_message_count: 0,
  message_count: 1,
  created_at: "2026-07-18T00:00:00Z",
  updated_at: "2026-07-18T00:00:00Z",
};
const assistant: ChatMessage = {
  id: "message-1",
  session_id: session.id,
  role: "assistant",
  content: "I prepared a governed evaluator proposal.",
  provider_response_id: "response-1",
  provider_request_id: "request-1",
  tool_calls: [{ call_id: "call-1", name: "propose_node", arguments: {} }],
  tool_results: [],
  linked_change_set_id: "change-set-1",
  usage: { total_tokens: 40 },
  latency_ms: 120,
  error_code: null,
  origin_type: "local",
  media: [],
  created_at: "2026-07-18T00:00:00Z",
};
const refetch = vi.fn().mockResolvedValue(undefined);
const authTest = vi.hoisted(() => ({ user: { id: "user-a" } as { id: string } | null, loading: false }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: authTest.user, loading: authTest.loading, can: () => true }) }));
afterEach(() => { assistant.error_code = null; session.credential_source = "system"; authTest.user = { id: "user-a" }; authTest.loading = false; });

vi.mock("@/lib/chat", () => ({
  listChatSessions: vi.fn(),
  createChatSession: vi.fn(),
  importChatGPTSharedChat: vi.fn(),
  listChatMessages: vi.fn(),
  sendChatMessage: vi.fn(),
  closeChatSession: vi.fn(),
  summarizeChatSession: vi.fn(),
  listPersonalChatModels: vi.fn().mockImplementation(async (provider) => ({ provider, models: ["personal-test-model", "deepseek-test"] })),
  verifyPersonalChatModel: vi.fn().mockImplementation(async (provider, _key, model) => ({ provider, model_name: model, verified: true })),
}));
vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    if (queryKey[0] === "chat-sessions") {
      return { data: { items: [session], total: 1 }, refetch, isLoading: false };
    }
    if (queryKey[0] === "ai-providers") {
      return { data: [
        { id: "deepseek", configured: true, reachable: null, chat_active: true, model: "deepseek-test" },
        { id: "openai", configured: false, reachable: null, chat_active: false, model: "gpt-test" },
      ] };
    }
    return { data: [assistant], refetch, isLoading: false };
  },
}));

it("shows local chat proposals and sends a bounded brainstorm turn", async () => {
  vi.mocked(sendChatMessage).mockResolvedValue({
    session,
    user_message: { ...assistant, id: "user-1", role: "user", content: "New idea" },
    assistant_message: assistant,
    change_set_id: "change-set-1",
  });
  render(<ChatPage />);

  await waitFor(() => expect(screen.getAllByText("Agent governance").length).toBeGreaterThan(0));
  expect(await screen.findByText("I prepared a governed evaluator proposal.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /reviewKnowledgeChanges/ })).toHaveAttribute(
    "href",
    "/graph/changes/change-set-1",
  );

  fireEvent.change(screen.getByLabelText("chatMessage"), { target: { value: "New idea" } });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  await waitFor(() => expect(sendChatMessage).toHaveBeenCalledWith("session-1", "New idea"));
});

it("turns selected message text into a reviewed composer draft without sending", async () => {
  vi.mocked(sendChatMessage).mockClear();
  render(<ChatPage />);

  const passage = await screen.findByText("I prepared a governed evaluator proposal.");
  const message = passage.closest<HTMLElement>("[data-chat-message-id]");
  expect(message).not.toBeNull();
  const textNode = passage.firstChild;
  expect(textNode).not.toBeNull();
  const selection = {
    isCollapsed: false,
    rangeCount: 1,
    anchorNode: textNode,
    focusNode: textNode,
    toString: () => "governed evaluator proposal",
    getRangeAt: () => ({
      getBoundingClientRect: () => ({
        left: 320, right: 490, top: 260, bottom: 280, width: 170, height: 20,
      }),
    }),
  } as unknown as Selection;
  vi.spyOn(window, "getSelection").mockReturnValue(selection);

  fireEvent.mouseUp(message!);
  fireEvent.click(await screen.findByRole("button", { name: /askAiAboutSelection/ }));

  expect(screen.getByLabelText("chatMessage")).toHaveValue(
    "askAboutSelectionPrompt\n\n> governed evaluator proposal",
  );
  expect(sendChatMessage).not.toHaveBeenCalled();
});

it("imports an official ChatGPT shared link as a local fork", async () => {
  vi.mocked(importChatGPTSharedChat).mockResolvedValue({
    ...session,
    id: "imported-session",
    source_type: "chatgpt_shared",
    source_url: "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc",
    source_snapshot_hash: "a".repeat(64),
    source_imported_at: "2026-07-18T00:00:00Z",
    imported_message_count: 2,
  });
  render(<ChatPage />);

  fireEvent.click(screen.getByRole("button", { name: "importChatGPT" }));
  fireEvent.change(screen.getByLabelText("chatGPTSharedLink"), {
    target: {
      value: "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc",
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "importChat" }));

  await waitFor(() => expect(importChatGPTSharedChat).toHaveBeenCalledWith({
    url: "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc",
    provider: "deepseek",
  }));
});

it("filters history without hiding the current conversation", async () => {
  render(<ChatPage />);
  await screen.findByText("I prepared a governed evaluator proposal.");
  fireEvent.change(screen.getByLabelText("Tìm cuộc trò chuyện"), { target: { value: "does not exist" } });
  expect(screen.getByText("Không tìm thấy cuộc trò chuyện phù hợp.")).toBeInTheDocument();
  expect(screen.getByText("I prepared a governed evaluator proposal.")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Tìm cuộc trò chuyện"), { target: { value: "AGENT" } });
  expect(screen.queryByText("Không tìm thấy cuộc trò chuyện phù hợp.")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Agent governance/ })).toHaveAttribute("aria-current", "true");
});

it("explains historical provider failures without rendering raw upstream text", async () => {
  assistant.error_code = "CHAT_PROVIDER_UNAVAILABLE";
  render(<ChatPage />);
  expect(await screen.findByText("Chưa thể hoàn tất câu trả lời")).toBeInTheDocument();
  expect(screen.queryByText(assistant.content)).not.toBeInTheDocument();
  expect(screen.getByText("CHAT_PROVIDER_UNAVAILABLE")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Chọn AI cho cuộc trò chuyện mới" }));
  expect(screen.getByText("Bắt đầu một mạch suy nghĩ mới")).toBeInTheDocument();
  expect(screen.getByLabelText("provider")).toHaveValue("deepseek");
});

async function enterPersonalApi() {
  fireEvent.click(screen.getByRole("button", { name: "API của tôi" }));
  fireEvent.change(await screen.findByLabelText("Nhà cung cấp API"), { target: { value: "deepseek" } });
  const key = screen.getByLabelText("API key cá nhân");
  expect(key).toHaveAttribute("type", "password");
  fireEvent.change(key, { target: { value: "synthetic-browser-api-key" } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  await screen.findByRole("option", { name: "personal-test-model" });
  if (session.credential_source !== "personal") fireEvent.change(screen.getByLabelText("Mô hình AI"), { target: { value: "personal-test-model" } });
  fireEvent.click(screen.getByRole("button", { name: "Kiểm tra và kết nối" }));
  await waitFor(() => expect(screen.queryByText("Kết nối API của bạn")).not.toBeInTheDocument());
}

it("uses personal credentials for creation without storing them in browser storage", async () => {
  const storage = vi.spyOn(Storage.prototype, "setItem");
  vi.mocked(createChatSession).mockResolvedValue({ ...session, credential_source: "personal" });
  render(<ChatPage />);
  await screen.findByText("I prepared a governed evaluator proposal.");
  await enterPersonalApi();
  expect(screen.getByLabelText("Nguồn API")).toHaveValue("personal");
  fireEvent.click(screen.getByRole("button", { name: "createChat" }));
  await waitFor(() => expect(createChatSession).toHaveBeenCalledWith(expect.objectContaining({
    provider: "deepseek", credential_source: "personal", model_name: "personal-test-model",
    personal_api_key: "synthetic-browser-api-key",
  })));
  expect(storage).not.toHaveBeenCalled();
  storage.mockRestore();
});

it("requires a personal key again after identity changes or the page unmounts", async () => {
  session.credential_source = "personal";
  vi.mocked(sendChatMessage).mockClear();
  const page = render(<ChatPage />);
  await screen.findByText("I prepared a governed evaluator proposal.");
  expect(screen.getByLabelText("chatMessage")).toBeDisabled();
  await enterPersonalApi();
  expect(screen.getByLabelText("chatMessage")).toBeEnabled();
  fireEvent.change(screen.getByLabelText("chatMessage"), { target: { value: "Use my key" } });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));
  await waitFor(() => expect(sendChatMessage).toHaveBeenCalledWith(
    "session-1", "Use my key", "synthetic-browser-api-key",
  ));
  authTest.user = { id: "user-b" };
  page.rerender(<ChatPage />);
  await waitFor(() => expect(screen.getByLabelText("chatMessage")).toBeDisabled());
  await enterPersonalApi();
  expect(screen.getByLabelText("chatMessage")).toBeEnabled();
  page.unmount();
  render(<ChatPage />);
  await waitFor(() => expect(screen.getByLabelText("chatMessage")).toBeDisabled());
});

it("forgets a configured key without closing or deleting the conversation", async () => {
  session.credential_source = "personal";
  render(<ChatPage />);
  await screen.findByText("I prepared a governed evaluator proposal.");
  await enterPersonalApi();
  fireEvent.click(screen.getByRole("button", { name: "API của tôi" }));
  expect(screen.getByLabelText("API key cá nhân")).toHaveValue("");
  fireEvent.click(screen.getByRole("button", { name: "Xóa khóa DeepSeek" }));
  fireEvent.click(screen.getByRole("button", { name: "Quay lại trò chuyện" }));
  expect(screen.getByLabelText("chatMessage")).toBeDisabled();
  expect(screen.getByText("I prepared a governed evaluator proposal.")).toBeInTheDocument();
});

it("keeps server-authenticated hydration stable but clears drafts on a real account switch", async () => {
  authTest.user = null;
  authTest.loading = true;
  const initial = { userId: "user-a", sessions: { items: [session], total: 1 },
    providers: [], selectedId: session.id, messages: [assistant] };
  const page = render(<ChatPage initial={initial} />);
  fireEvent.change(await screen.findByLabelText("chatMessage"), { target: { value: "Hydration draft" } });
  authTest.user = { id: "user-a" };
  authTest.loading = false;
  page.rerender(<ChatPage initial={initial} />);
  expect(screen.getByLabelText("chatMessage")).toHaveValue("Hydration draft");
  authTest.user = { id: "user-b" };
  page.rerender(<ChatPage initial={initial} />);
  expect(screen.getByLabelText("chatMessage")).toHaveValue("");
});
