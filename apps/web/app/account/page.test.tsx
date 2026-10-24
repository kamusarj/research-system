import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import AccountPage from "./page";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    enabled: true,
    user: { id: "member-1", name: "An", email: "an@example.com", role: "researcher" },
  }),
}));

afterEach(() => vi.unstubAllGlobals());

function fill(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText("Mật khẩu hiện tại"), { target: { value: current } });
  fireEvent.change(screen.getByLabelText("Mật khẩu mới"), { target: { value: next } });
  fireEvent.change(screen.getByLabelText("Nhập lại mật khẩu mới"), { target: { value: confirm } });
  fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));
}

it("rejects a mismatched confirmation without calling the API", () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<AccountPage />);

  fill("temporary-pass-123", "new-password-4567", "different-password-1");

  expect(screen.getByRole("alert")).toHaveTextContent("chưa khớp");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("changes the password and reports a wrong current password", async () => {
  let status = 400;
  const fetchMock = vi.fn(async () => status === 400
    ? new Response(JSON.stringify({ error: { code: "PASSWORD_INCORRECT" } }), { status })
    : new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<AccountPage />);

  fill("wrong-password-000", "new-password-4567", "new-password-4567");
  expect(await screen.findByRole("alert")).toHaveTextContent("Mật khẩu hiện tại không đúng.");

  status = 204;
  fill("temporary-pass-123", "new-password-4567", "new-password-4567");
  expect(await screen.findByRole("status")).toHaveTextContent("Đã đổi mật khẩu");
  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/v1/auth/me/password",
    expect.objectContaining({ method: "POST" }),
  );
});
