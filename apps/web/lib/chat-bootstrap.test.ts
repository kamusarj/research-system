import { afterEach, expect, it, vi } from "vitest";
import { loadChatBootstrap } from "./chat-bootstrap";

afterEach(() => vi.unstubAllGlobals());

it("does not fetch private data when session authentication fails", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("", { status: 401 }));
  vi.stubGlobal("fetch", fetcher);
  expect(await loadChatBootstrap("invalid=fixture", "http://api:8000")).toBeUndefined();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("forwards the session with no-store on every server fetch and binds data to its user", async () => {
  const fetcher = vi.fn(async (url: string) => {
    const body = url.endsWith("/auth/me") ? { enabled: true, user: { id: "owner-fixture" } }
      : url.endsWith("/chat/sessions") ? { items: [{ id: "session-fixture" }], total: 1 }
      : url.endsWith("/ai/providers") ? [] : [{ id: "message-fixture" }];
    return Response.json(body);
  });
  vi.stubGlobal("fetch", fetcher);
  const result = await loadChatBootstrap("session=synthetic", "http://api:8000");
  expect(result?.userId).toBe("owner-fixture");
  expect(result?.selectedId).toBe("session-fixture");
  expect(result?.messages).toHaveLength(1);
  for (const call of fetcher.mock.calls as unknown as [string, RequestInit][]) {
    expect(call[1].headers).toEqual({ Cookie: "session=synthetic" });
    expect(call[1].cache).toBe("no-store");
  }
});

it("returns to the existing client recovery flow on an unavailable backend", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network failure")));
  expect(await loadChatBootstrap("", "http://api:8000")).toBeUndefined();
});

it("sends only the newest window to hydration while preserving the full history count", async () => {
  const messages = Array.from({ length: 24 }, (_, index) => ({ id: `message-${index + 1}` }));
  vi.stubGlobal("fetch", vi.fn(async (url: string) => Response.json(
    url.endsWith("/auth/me") ? { enabled: true, user: { id: "owner-fixture" } }
      : url.endsWith("/chat/sessions") ? { items: [{ id: "session-fixture" }], total: 1 }
      : url.endsWith("/ai/providers") ? [] : messages,
  )));
  const result = await loadChatBootstrap("session=synthetic", "http://api:8000");
  expect(result?.messages.map((message) => message.id)).toEqual(messages.slice(-8).map((message) => message.id));
  expect(result?.messageTotal).toBe(24);
});

it("keeps disabled-auth and browser-fixture data on the existing client path", async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ enabled: false, user: { id: "local-user" } }));
  vi.stubGlobal("fetch", fetcher);
  expect(await loadChatBootstrap("", "http://api:8000")).toBeUndefined();
  expect(fetcher).toHaveBeenCalledTimes(1);
});
