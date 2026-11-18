import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ChatLocalModelSettings } from "./chat-local-model-settings";
import { ApiError } from "@/lib/api";
import { listLocalChatModels, verifyLocalChatModel, type LocalChatSelection } from "@/lib/chat";

vi.mock("@/lib/chat", () => ({ listLocalChatModels: vi.fn(), verifyLocalChatModel: vi.fn() }));
const onVerifiedChange = vi.fn();
const props = { provider: "ollama" as const, preferredModel: "model-b", onVerifiedChange };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listLocalChatModels).mockImplementation(async (provider) => ({ provider, models: ["model-a", "model-b"] }));
  vi.mocked(verifyLocalChatModel).mockImplementation(async (provider, model_name) => ({ provider, model_name, verified: true }));
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  return { promise: new Promise<T>((done) => { resolve = done; }), resolve: (value: T) => resolve(value) };
}
async function load() {
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình cục bộ" }));
  await screen.findByRole("option", { name: "model-b" });
}
function verify() { fireEvent.click(screen.getByRole("button", { name: "Kiểm tra mô hình cục bộ" })); }
function positiveSelections() { return onVerifiedChange.mock.calls.filter(([selection]) => selection !== null); }

it("loads an installed model list without inference and verifies only after explicit selection and click", async () => {
  render(<ChatLocalModelSettings {...props} />);
  expect(listLocalChatModels).not.toHaveBeenCalled();
  expect(verifyLocalChatModel).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Mô hình cục bộ")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Kiểm tra mô hình cục bộ" })).toBeDisabled();
  expect(screen.queryByLabelText("API key cá nhân")).not.toBeInTheDocument();
  await load();
  expect(listLocalChatModels).toHaveBeenCalledWith("ollama", expect.any(AbortSignal));
  expect(screen.getByLabelText("Mô hình cục bộ")).toHaveValue("model-b");
  expect(positiveSelections()).toHaveLength(0);
  expect(verifyLocalChatModel).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Mô hình cục bộ"), { target: { value: "model-a" } });
  verify();
  await waitFor(() => expect(onVerifiedChange).toHaveBeenLastCalledWith({ provider: "ollama", model_name: "model-a" }));
  expect(verifyLocalChatModel).toHaveBeenCalledWith("ollama", "model-a", expect.any(AbortSignal));
  expect(screen.getByRole("status")).toHaveTextContent("Đã kiểm tra mô hình model-a");
});

it("clears a successful verification when the selected model changes or the inventory reloads", async () => {
  render(<ChatLocalModelSettings {...props} />);
  await load(); verify();
  await waitFor(() => expect(positiveSelections()).toHaveLength(1));
  fireEvent.change(screen.getByLabelText("Mô hình cục bộ"), { target: { value: "model-a" } });
  expect(onVerifiedChange).toHaveBeenLastCalledWith(null);
  expect(screen.queryByText(/Đã kiểm tra mô hình/)).not.toBeInTheDocument();
  verify();
  await waitFor(() => expect(positiveSelections()).toHaveLength(2));
  fireEvent.click(screen.getByRole("button", { name: "Tải lại danh sách mô hình cục bộ" }));
  expect(onVerifiedChange).toHaveBeenLastCalledWith(null);
  expect(screen.getByLabelText("Mô hình cục bộ")).toBeDisabled();
  await screen.findByRole("option", { name: "model-b" });
  expect(screen.queryByText(/Đã kiểm tra mô hình/)).not.toBeInTheDocument();
});

it("discards a late model list after the provider changes", async () => {
  const old = deferred<{ provider: "ollama"; models: string[] }>();
  vi.mocked(listLocalChatModels).mockReturnValueOnce(old.promise);
  const view = render(<ChatLocalModelSettings {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình cục bộ" }));
  const signal = vi.mocked(listLocalChatModels).mock.calls[0][1];
  view.rerender(<ChatLocalModelSettings {...props} provider="local_openai" />);
  expect(signal?.aborted).toBe(true);
  await act(async () => old.resolve({ provider: "ollama", models: ["stale-model"] }));
  expect(screen.queryByRole("option", { name: "stale-model" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Mô hình cục bộ")).toBeDisabled();
  await load();
  expect(listLocalChatModels).toHaveBeenLastCalledWith("local_openai", expect.any(AbortSignal));
});

it.each(["model", "provider", "reload", "unmount"])("ignores a late successful probe after %s changes", async (change) => {
  const old = deferred<LocalChatSelection & { verified: true }>();
  vi.mocked(verifyLocalChatModel).mockReturnValueOnce(old.promise);
  const view = render(<ChatLocalModelSettings {...props} />);
  await load(); verify();
  const signal = vi.mocked(verifyLocalChatModel).mock.calls[0][2];
  if (change === "model") fireEvent.change(screen.getByLabelText("Mô hình cục bộ"), { target: { value: "model-a" } });
  else if (change === "provider") view.rerender(<ChatLocalModelSettings {...props} provider="local_openai" />);
  else if (change === "reload") fireEvent.click(screen.getByRole("button", { name: "Tải lại danh sách mô hình cục bộ" }));
  else view.unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => old.resolve({ provider: "ollama", model_name: "model-b", verified: true }));
  expect(positiveSelections()).toHaveLength(0);
});

it.each(["CHAT_MODEL_UNAVAILABLE", "CHAT_MODEL_INCOMPATIBLE", "CHAT_PROVIDER_UNAVAILABLE", "CHAT_PROVIDER_TIMEOUT"])("keeps a failed local probe unverified and hides upstream text: %s", async (code) => {
  vi.mocked(verifyLocalChatModel).mockRejectedValue(new ApiError("http://private-endpoint.invalid secret upstream text", code, 422));
  render(<ChatLocalModelSettings {...props} />);
  await load(); verify();
  const error = await screen.findByRole("alert");
  expect(error).not.toHaveTextContent("private-endpoint");
  expect(error).not.toHaveTextContent("upstream text");
  expect(positiveSelections()).toHaveLength(0);
  expect(screen.getByRole("button", { name: "Kiểm tra mô hình cục bộ" })).toBeEnabled();
});

it("explains an empty inventory and never probes or offers a download", async () => {
  vi.mocked(listLocalChatModels).mockResolvedValue({ provider: "ollama", models: [] });
  render(<ChatLocalModelSettings {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình cục bộ" }));
  expect(await screen.findByText(/Chưa có mô hình nào sẵn sàng/)).toHaveAttribute("role", "status");
  expect(screen.getByLabelText("Mô hình cục bộ")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Kiểm tra mô hình cục bộ" })).toBeDisabled();
  expect(verifyLocalChatModel).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: /tải mô hình|cài mô hình/i })).not.toBeInTheDocument();
});

it("does not accept a probe for another provider or model", async () => {
  vi.mocked(verifyLocalChatModel).mockResolvedValue({ provider: "local_openai", model_name: "another-model", verified: true });
  render(<ChatLocalModelSettings {...props} />);
  await load(); verify();
  expect(await screen.findByRole("alert")).toHaveTextContent("chưa xác nhận đúng mô hình");
  expect(positiveSelections()).toHaveLength(0);
});

it("does not expose an unknown network error or endpoint", async () => {
  vi.mocked(listLocalChatModels).mockRejectedValue(new Error("secret http://private-endpoint.invalid/v1"));
  render(<ChatLocalModelSettings {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Tải danh sách mô hình cục bộ" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("liên hệ quản trị viên");
  expect(screen.getByRole("alert")).not.toHaveTextContent("private-endpoint");
  expect(screen.getByRole("button", { name: "Kiểm tra mô hình cục bộ" })).toBeDisabled();
});
