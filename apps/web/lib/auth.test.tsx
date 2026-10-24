import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { AUTH_EXPIRED_EVENT } from "@/lib/api";
import { AuthGate, AuthProvider, useAuth } from "@/lib/auth";
import { LocaleProvider } from "@/lib/i18n";

const viewer = {
  id: "viewer-1",
  name: "Read only",
  email: "viewer@example.com",
  role: "viewer" as const,
  active: true,
  password_configured: true,
};

function Probe() {
  const { user, can } = useAuth();
  return <div>{user?.name} · write:{String(can("researcher"))}</div>;
}

function renderAuth() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider><AuthProvider><AuthGate><Probe /></AuthGate></AuthProvider></LocaleProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

it("gates an enabled workspace and restores the authenticated viewer role", async () => {
  const requests: Array<[string, RequestInit | undefined]> = [];
  let signedIn = false;
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    requests.push([url, init]);
    if (url.endsWith("/auth/config")) {
      return new Response(JSON.stringify({ enabled: true, mode: "local", csrf_cookie_name: "research_csrf" }), { status: 200 });
    }
    if (url.endsWith("/auth/me") && !signedIn) {
      return new Response(JSON.stringify({ error: { code: "AUTH_REQUIRED", message: "Authentication is required" } }), { status: 401 });
    }
    if (url.endsWith("/auth/login")) signedIn = true;
    return new Response(JSON.stringify({ enabled: true, user: viewer }), { status: 200 });
  }));

  renderAuth();
  await screen.findByRole("heading", { name: "Đăng nhập" });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: viewer.email } });
  fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "viewer-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

  await screen.findByText("Read only · write:false");
  const login = requests.find(([url]) => url.endsWith("/auth/login"));
  expect(login?.[1]).toMatchObject({ method: "POST", credentials: "include" });
});

it("keeps trusted local mode compatible without a login form", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/auth/config")) {
      return new Response(JSON.stringify({ enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" }), { status: 200 });
    }
    return new Response(JSON.stringify({ enabled: false, user: { ...viewer, id: "local-user", name: "Local owner", role: "owner" } }), { status: 200 });
  }));

  renderAuth();
  await waitFor(() => expect(screen.getByText("Local owner · write:true")).toBeInTheDocument());
  expect(screen.queryByRole("heading", { name: "Đăng nhập" })).not.toBeInTheDocument();
});

it("returns to the sign-in screen when the session expires mid-use", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/auth/config")) {
      return new Response(JSON.stringify({ enabled: true, mode: "local", csrf_cookie_name: "research_csrf" }), { status: 200 });
    }
    return new Response(JSON.stringify({ enabled: true, user: viewer }), { status: 200 });
  }));

  renderAuth();
  await screen.findByText("Read only · write:false");
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));

  await screen.findByRole("heading", { name: "Đăng nhập" });
  expect(screen.getByRole("status")).toHaveTextContent("Phiên đăng nhập đã hết hạn");
});

it("explains a wrong password and a cookie the browser refused", async () => {
  let loginStatus = 401;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/auth/config")) {
      return new Response(JSON.stringify({ enabled: true, mode: "local", csrf_cookie_name: "research_csrf" }), { status: 200 });
    }
    if (url.endsWith("/auth/login")) {
      return new Response(JSON.stringify(loginStatus === 401 ? { error: { code: "AUTH_REQUIRED" } } : { enabled: true, user: viewer }), { status: loginStatus });
    }
    return new Response(JSON.stringify({ error: { code: "AUTH_REQUIRED" } }), { status: 401 });
  }));

  renderAuth();
  await screen.findByRole("heading", { name: "Đăng nhập" });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: viewer.email } });
  fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "viewer-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không đúng.");

  loginStatus = 200;
  fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("https://"));
});
