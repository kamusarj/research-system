import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatGPTPlanCard } from "./chatgpt-plan-card";

const base = {
  enabled: true,
  mode: "local",
  email: null,
  model: null,
  models: [],
  use_by_default: true,
  last_error_code: null,
  connected_at: null,
  last_used_at: null,
  usage_url: "https://chatgpt.com/settings/usage",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

it("starts the ChatGPT sign-in when the user is not connected", async () => {
  const fetchMock = vi.fn(async (url: string) => url.endsWith("/start")
    ? json({ authorize_url: "https://auth.openai.com/api/accounts/authorize?state=x" })
    : json({ ...base, status: "not_connected" }));
  vi.stubGlobal("fetch", fetchMock);
  const navigate = vi.fn();
  render(<ChatGPTPlanCard navigate={navigate} />);

  fireEvent.click(await screen.findByRole("button", { name: "Tiếp tục với ChatGPT" }));

  await waitFor(() => expect(navigate).toHaveBeenCalledWith("https://auth.openai.com/api/accounts/authorize?state=x"));
  expect(screen.getByText(/127\.0\.0\.1/)).toBeInTheDocument();
});

it("shows the active plan, the usage link and the first-connection welcome once", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => json({
    ...base,
    mode: "partner",
    status: "active",
    email: "an@example.com",
    model: "gpt-6.1-sol",
    models: [{ slug: "gpt-6.1-sol", display_name: "GPT-6.1 Sol" }],
  })));
  render(<ChatGPTPlanCard justConnected />);

  expect(await screen.findByText("Đang dùng gói ChatGPT")).toBeInTheDocument();
  expect(screen.getByText("an@example.com")).toBeInTheDocument();
  expect(screen.getByLabelText("Model")).toHaveValue("gpt-6.1-sol");
  const links = screen.getAllByRole("link", { name: "Quản lý mức dùng" });
  expect(links[0]).toHaveAttribute("href", "https://chatgpt.com/settings/usage");
  expect(links[0]).toHaveAttribute("rel", "noopener noreferrer");

  fireEvent.click(screen.getByRole("button", { name: "Đã hiểu" }));
  expect(screen.queryByText("Bạn đang dùng gói ChatGPT của mình")).not.toBeInTheDocument();
  expect(window.localStorage.getItem("chatgpt-plan-welcomed")).toBe("1");
});

it("explains when the administrator has not enabled the feature", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => json({ ...base, enabled: false, status: "not_connected" })));
  render(<ChatGPTPlanCard />);
  expect(await screen.findByText(/chưa bật tính năng/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tiếp tục với ChatGPT" })).not.toBeInTheDocument();
});

it("asks to reconnect after the session expired", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => json({ ...base, status: "reauth_required", email: "an@example.com" })));
  render(<ChatGPTPlanCard />);
  expect(await screen.findByRole("alert")).toHaveTextContent("kết nối lại");
  expect(screen.getByRole("button", { name: "Tiếp tục với ChatGPT" })).toBeInTheDocument();
});
