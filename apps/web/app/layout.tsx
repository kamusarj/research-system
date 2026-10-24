import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Hệ thống nghiên cứu",
  description: "Thư viện nghiên cứu và không gian xử lý nguồn cục bộ",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f1f5f3" },
    { media: "(prefers-color-scheme: dark)", color: "#0c1615" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // data-theme do script dưới đặt trước khi React hydrate, nên bỏ qua khác biệt thuộc tính này.
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body><Providers><AppShell>{children}</AppShell></Providers></body>
    </html>
  );
}
