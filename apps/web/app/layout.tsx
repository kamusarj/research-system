import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "@fontsource-variable/inter";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";
import { Providers } from "./providers";

const interLatin = localFont({
  src: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2",
  variable: "--font-inter-latin", weight: "100 900", display: "swap", adjustFontFallback: false,
});
const interVietnamese = localFont({
  src: "../node_modules/@fontsource-variable/inter/files/inter-vietnamese-wght-normal.woff2",
  variable: "--font-inter-vietnamese", weight: "100 900", display: "swap", adjustFontFallback: false,
});
const interExtended = localFont({
  src: "../node_modules/@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2",
  variable: "--font-inter-extended", weight: "100 900", display: "swap", adjustFontFallback: false,
  preload: false,
});

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
      <body className={`${interLatin.variable} ${interVietnamese.variable} ${interExtended.variable}`}>
        <Providers><AppShell>{children}</AppShell></Providers>
      </body>
    </html>
  );
}
