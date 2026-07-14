"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/i18n";

const links = [
  ["/", "dashboard", "◫"], ["/ingestion", "intake", "↗"], ["/research", "research", "▤"],
  ["/search", "search", "⌕"], ["/graph", "graph", "⌘"], ["/gaps", "gaps", "◇"],
  ["/collector", "collector", "⇣"], ["/training", "training", "△"],
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { locale, setLocale, t } = useI18n();
  return <div className="shell">
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark">R</span><span>RESEARCH<br /><small>INTELLIGENCE</small></span></Link>
      <nav className="nav">{links.map(([href, key, icon]) => <Link className={pathname === href ? "active" : ""} key={href} href={href}><span>{icon}</span>{t(key)}</Link>)}</nav>
      <div className="locale-switch"><span>{t("language")}</span><div><button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>EN</button><button className={locale === "vi" ? "active" : ""} onClick={() => setLocale("vi")}>VI</button></div></div>
    </aside>
    <main className="content">{children}</main>
  </div>;
}
