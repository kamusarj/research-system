import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ChatApiSettings } from "./chat-api-settings";
import { ApiError, vietnameseApiErrorMessage } from "@/lib/api";
import { listPersonalChatModels, verifyPersonalChatModel } from "@/lib/chat";

vi.mock("@/lib/chat", () => ({ listPersonalChatModels: vi.fn(), verifyPersonalChatModel: vi.fn() }));
const KEY = "synthetic-browser-api-key";
const onSave = vi.fn();
const onClose = vi.fn();
const props = { initialProvider: "openai", models: {}, connections: {}, onSave, onClose, onForget: vi.fn() };
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listPersonalChatModels).mockResolvedValue({ provider: "openai", models: ["model-a", "model-b"] });
  vi.mocked(verifyPersonalChatModel).mockImplementation(async (provider, _key, model) => ({ provider, model_name: model, verified: true }));
});

async function load() {
  fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  await screen.findByRole("option", { name: "model-a" });
}
function verify() { fireEvent.click(screen.getByRole("button", { name: "Kiểm tra và kết nối" })); }
function deferred<T>() {
  let resolve!: (value: T) => void;
  return { promise: new Promise<T>((done) => { resolve = done; }), resolve: (value: T) => resolve(value) };
}

it("loads models without spending tokens, probes the selection only on explicit click and saves only after success", async () => {
  render(<ChatApiSettings {...props} />);
  expect(screen.getByLabelText("Mô hình AI")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
  await load();
  expect(listPersonalChatModels).toHaveBeenCalledWith("openai", KEY, expect.any(AbortSignal));
  expect(verifyPersonalChatModel).not.toHaveBeenCalled();
  expect(onSave).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Mô hình AI"), { target: { value: "model-b" } });
  expect(screen.getByText(/có thể phát sinh phí nhỏ/)).toBeInTheDocument();
  verify();
  await waitFor(() => expect(onSave).toHaveBeenCalledWith("openai", { apiKey: KEY, model: "model-b", verifiedModels: ["model-b"] }));
  expect(verifyPersonalChatModel).toHaveBeenCalledWith("openai", KEY, "model-b", expect.any(AbortSignal));
  expect(screen.getByLabelText("API key cá nhân")).toHaveValue("");
});

it.each(["CHAT_API_KEY_INVALID", "CHAT_CREDIT_EXHAUSTED", "CHAT_QUOTA_EXCEEDED", "CHAT_SPEND_LIMIT_REACHED", "CHAT_USAGE_LIMIT_REACHED", "CHAT_MODEL_UNAVAILABLE", "CHAT_MODEL_INCOMPATIBLE", "CHAT_API_ACCESS_DENIED", "CHAT_PROVIDER_RATE_LIMITED", "CHAT_PROVIDER_TIMEOUT"])("does not save when verification fails: %s", async (code) => {
  vi.mocked(verifyPersonalChatModel).mockRejectedValue(new ApiError(`unsafe ${KEY}`, code, 422));
  render(<ChatApiSettings {...props} />);
  await load(); verify();
  expect(await screen.findByRole("alert")).toHaveTextContent(vietnameseApiErrorMessage(code));
  expect(screen.getByRole("alert")).not.toHaveTextContent(KEY);
  expect(onSave).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeEnabled();
  vi.mocked(verifyPersonalChatModel).mockResolvedValue({ provider: "openai", model_name: "model-b", verified: true });
  fireEvent.change(screen.getByLabelText("Mô hình AI"), { target: { value: "model-b" } });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  verify();
  await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
});

it("shows invalid key on discovery and never enables verification", async () => {
  vi.mocked(listPersonalChatModels).mockRejectedValue(new ApiError(KEY, "CHAT_API_KEY_INVALID", 422));
  render(<ChatApiSettings {...props} />);
  fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: "short" } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  expect(screen.getByRole("alert")).toHaveTextContent("chưa đúng định dạng");
  expect(listPersonalChatModels).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Không xác thực được API key");
  expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
  expect(onSave).not.toHaveBeenCalled();
});

it("explains an empty model list", async () => {
  vi.mocked(listPersonalChatModels).mockResolvedValue({ provider: "openai", models: [] });
  render(<ChatApiSettings {...props} />);
  fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  await screen.findByText(/API không trả về mô hình nào/);
  expect(screen.getByLabelText("Mô hình AI")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
});

it("discards a stale model list after changing key or provider", async () => {
  const result = deferred<{ provider: string; models: string[] }>();
  vi.mocked(listPersonalChatModels).mockReturnValue(result.promise);
  render(<ChatApiSettings {...props} />);
  fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình" }));
  const signal = vi.mocked(listPersonalChatModels).mock.calls[0][2];
  fireEvent.change(screen.getByLabelText("Nhà cung cấp API"), { target: { value: "deepseek" } });
  expect(signal?.aborted).toBe(true);
  expect(screen.getByLabelText("API key cá nhân")).toHaveValue("");
  await act(async () => result.resolve({ provider: "openai", models: ["stale-model"] }));
  expect(screen.queryByRole("option", { name: "stale-model" })).not.toBeInTheDocument();
});

it.each(["key", "model", "close", "unmount"])("never saves a stale successful probe after %s changes", async (change) => {
  const result = deferred<{ provider: string; model_name: string; verified: true }>();
  vi.mocked(verifyPersonalChatModel).mockReturnValue(result.promise);
  const view = render(<ChatApiSettings {...props} />);
  await load(); verify();
  const signal = vi.mocked(verifyPersonalChatModel).mock.calls[0][3];
  if (change === "key") fireEvent.change(screen.getByLabelText("API key cá nhân"), { target: { value: "synthetic-new-key" } });
  else if (change === "model") fireEvent.change(screen.getByLabelText("Mô hình AI"), { target: { value: "model-b" } });
  else if (change === "close") fireEvent.click(screen.getByRole("button", { name: "Quay lại trò chuyện" }));
  else view.unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => result.resolve({ provider: "openai", model_name: "model-a", verified: true }));
  expect(onSave).not.toHaveBeenCalled();
  if (change === "key") expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
});

it("checks the pinned conversation model and does not substitute the first model", async () => {
  render(<ChatApiSettings {...props} pinnedModel="model-b" />);
  await load();
  expect(screen.getByLabelText("Mô hình AI")).toHaveValue("model-b");
  expect(screen.getByLabelText("Mô hình AI")).toBeDisabled();
  verify();
  await waitFor(() => expect(verifyPersonalChatModel).toHaveBeenCalledWith("openai", KEY, "model-b", expect.any(AbortSignal)));
});

it("requires another key when the old conversation model is absent", async () => {
  render(<ChatApiSettings {...props} pinnedModel="missing-old-model" />);
  await load();
  expect(screen.getByRole("alert")).toHaveTextContent("missing-old-model");
  expect(screen.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
  expect(onSave).not.toHaveBeenCalled();
});
