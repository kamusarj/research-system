"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { AuthGate, AuthProvider } from "@/lib/auth";
import { LocaleProvider } from "@/lib/i18n";

// Lỗi 4xx (hết phiên, thiếu quyền, không tìm thấy) không tự khỏi khi thử lại; chỉ thử lại lỗi
// mạng/máy chủ để giao diện báo lỗi ngay thay vì chờ ba lượt.
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery } } }),
  );
  return (
    <QueryClientProvider client={client}>
      <LocaleProvider><AuthProvider><AuthGate>{children}</AuthGate></AuthProvider></LocaleProvider>
    </QueryClientProvider>
  );
}
