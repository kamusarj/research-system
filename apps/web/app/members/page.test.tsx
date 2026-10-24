import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import MembersPage from "./page";

const auth = vi.hoisted(() => ({ role: "owner" as "owner" | "researcher" }));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    enabled: true,
    user: { id: "owner-1", name: "Linh", email: "owner@example.com", role: auth.role },
    can: (role: string) => auth.role === "owner" || role !== "owner",
  }),
}));

const owner = { id: "owner-1", name: "Linh", email: "owner@example.com", role: "owner", active: true, password_configured: true };
const member = { id: "member-1", name: "An", email: "an@example.com", role: "researcher", active: true, password_configured: true };

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MembersPage /></QueryClientProvider>);
}

let requests: Array<{ url: string; method: string; body: Record<string, unknown> | null }> = [];

beforeEach(() => {
  auth.role = "owner";
  requests = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    requests.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null });
    if (method === "POST" && url.endsWith("/auth/users")) {
      const body = JSON.parse(String(init?.body));
      if (body.email === owner.email) {
        return new Response(JSON.stringify({ error: { code: "INVALID_REQUEST" } }), { status: 409 });
      }
      return new Response(JSON.stringify({ ...member, id: "member-2", ...body }), { status: 201 });
    }
    if (method === "PATCH") return new Response(JSON.stringify(member), { status: 200 });
    return new Response(JSON.stringify([owner, member]), { status: 200 });
  }));
  vi.stubGlobal("confirm", vi.fn(() => true));
});

afterEach(() => vi.unstubAllGlobals());

it("creates a member account with a generated temporary password", async () => {
  renderPage();
  await screen.findByText("an@example.com");

  fireEvent.change(screen.getByLabelText("Họ tên"), { target: { value: "Bình" } });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "binh@example.com" } });
  fireEvent.click(screen.getByRole("button", { name: "Tạo ngẫu nhiên" }));
  fireEvent.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

  await screen.findByText(/Đã tạo tài khoản cho Bình/);
  const created = requests.find((request) => request.method === "POST");
  expect(created?.body).toMatchObject({ name: "Bình", email: "binh@example.com", role: "researcher" });
  expect(String(created?.body?.password)).toHaveLength(16);
});

it("explains a duplicate email and keeps the owner from demoting themself", async () => {
  renderPage();
  await screen.findByText("an@example.com");

  expect(screen.getByLabelText("Vai trò của Linh")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Họ tên"), { target: { value: "Linh" } });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: owner.email } });
  fireEvent.change(screen.getByLabelText("Mật khẩu tạm"), { target: { value: "temporary-pass-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Email này đã có tài khoản.");
});

it("resets a member password and shows the temporary value once", async () => {
  renderPage();
  const card = (await screen.findByText("an@example.com")).closest("article")!;

  fireEvent.click(within(card).getByRole("button", { name: "Đặt lại mật khẩu" }));

  await waitFor(() => expect(requests.some((request) => request.method === "PATCH")).toBe(true));
  const patch = requests.find((request) => request.method === "PATCH");
  expect(patch?.url).toMatch(/\/auth\/users\/member-1$/);
  expect(await screen.findByRole("status")).toHaveTextContent(String(patch?.body?.password));
});

it("tells non-owners that only the owner manages members", () => {
  auth.role = "researcher";
  renderPage();

  expect(screen.getByText(/Chỉ chủ sở hữu được quản lý thành viên/)).toBeInTheDocument();
  expect(requests).toHaveLength(0);
});
