import { api } from "@/lib/api";
import type { AuthUser, Role } from "@/lib/auth";

export type MemberCreate = { name: string; email: string; role: Role; password: string };
export type MemberUpdate = Partial<{ name: string; role: Role; active: boolean; password: string }>;

export const MIN_PASSWORD_LENGTH = 12;

export function listMembers() {
  return api<AuthUser[]>("/auth/users");
}

export function createMember(data: MemberCreate) {
  return api<AuthUser>("/auth/users", { method: "POST", body: JSON.stringify(data) });
}

export function updateMember(id: string, data: MemberUpdate) {
  return api<AuthUser>(`/auth/users/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export function changeOwnPassword(currentPassword: string, newPassword: string) {
  return api<void>("/auth/me/password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

const PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";

/** Mật khẩu tạm ngẫu nhiên, đủ dài và tránh ký tự dễ nhầm (0/O, 1/l/I). */
export function generateTemporaryPassword(length = 16): string {
  const values = new Uint32Array(length);
  crypto.getRandomValues(values);
  return Array.from(values, (value) => PASSWORD_ALPHABET[value % PASSWORD_ALPHABET.length]).join("");
}
