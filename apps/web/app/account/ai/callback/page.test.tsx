import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import ChatGPTPlanCallbackPage from "./page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
  window.history.replaceState(null, "", "/");
});

it("completes the connection in this session and strips the code from the address bar", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "active" }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState(null, "", "/account/ai/callback?code=one-time&state=state-value-123456&client_id=oaiapp_x&scope=openid");

  render(<ChatGPTPlanCallbackPage />);

  expect(window.location.search).toBe("");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/account?chatgpt=connected"));
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("/api/v1/ai-connections/chatgpt/complete");
  expect(JSON.parse(String(init.body))).toEqual({ state: "state-value-123456", code: "one-time", client_id: "oaiapp_x" });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("shows an error instead of calling the API when the link has no state", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState(null, "", "/account/ai/callback?code=one-time");

  render(<ChatGPTPlanCallbackPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("không hợp lệ");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("reports a rejected connection with the server's reason", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "CHATGPT_PLAN_STATE_INVALID" } }), { status: 400 })));
  window.history.replaceState(null, "", "/account/ai/callback?code=c&state=state-value-123456");

  render(<ChatGPTPlanCallbackPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Phiên kết nối ChatGPT đã hết hạn");
  expect(replace).not.toHaveBeenCalled();
});
