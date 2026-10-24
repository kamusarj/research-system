"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { ThemeToggle } from "@/components/theme-toggle";

type IconName = "dashboard" | "research" | "deep" | "documents" | "sources" | "search" | "graph" | "changes" | "chat" | "gaps" | "collector" | "members";

const navigation: { href: string; key: string; icon: IconName }[] = [
  { href: "/", key: "dashboard", icon: "dashboard" },
  { href: "/research", key: "research", icon: "research" },
  { href: "/research/new", key: "deepResearchNav", icon: "deep" },
  { href: "/documents", key: "documentWorkspace", icon: "documents" },
  { href: "/ingestion", key: "sources", icon: "sources" },
  { href: "/search", key: "search", icon: "search" },
  { href: "/graph", key: "graph", icon: "graph" },
  { href: "/graph/changes", key: "graphChanges", icon: "changes" },
  { href: "/chat", key: "brainstormChat", icon: "chat" },
  { href: "/gaps", key: "gaps", icon: "gaps" },
  { href: "/collector", key: "collector", icon: "collector" },
];

// Chỉ hiện với chủ sở hữu; máy chủ vẫn tự kiểm tra quyền.
const adminNavigation: { href: string; key: string; icon: IconName }[] = [
  { href: "/members", key: "members", icon: "members" },
];

const navigationGroups = [
  { key: "navLibrary", items: navigation.slice(0, 6) },
  { key: "navIntelligence", items: navigation.slice(6) },
];

function NavIcon({ name }: { name: IconName }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "dashboard") return <svg {...common}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>;
  if (name === "research") return <svg {...common}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></svg>;
  if (name === "deep") return <svg {...common}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.6-4.6" /><path d="m8 11 2 2 4-4" /></svg>;
  if (name === "documents") return <svg {...common}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6M8 13h8M8 17h6" /></svg>;
  if (name === "sources") return <svg {...common}><path d="M12 5v14M5 12h14" /><circle cx="12" cy="12" r="10" /></svg>;
  if (name === "search") return <svg {...common}><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>;
  if (name === "graph") return <svg {...common}><circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><path d="m7 7 4 9m6-9-4 9M7 6h10" /></svg>;
  if (name === "changes") return <svg {...common}><path d="M4 6h16M4 12h10M4 18h7" /><path d="m17 15 3 3-3 3" /></svg>;
  if (name === "chat") return <svg {...common}><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z" /><path d="M8 9h8M8 13h5" /></svg>;
  if (name === "gaps") return <svg {...common}><path d="M12 2 2 7l10 5 10-5-10-5Z" /><path d="m2 17 10 5 10-5M2 12l10 5 10-5" /></svg>;
  if (name === "members") return <svg {...common}><circle cx="9" cy="8" r="3" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M16 4a3 3 0 0 1 0 6M21 20a6 6 0 0 0-4-5.6" /></svg>;
  if (name === "collector") return <svg {...common}><path d="M4 11a9 9 0 0 1 9 9" /><path d="M4 4a16 16 0 0 1 16 16" /><circle cx="5" cy="19" r="1" /></svg>;
  return <svg {...common}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /><path d="M9 7h7M9 11h7" /></svg>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { t } = useI18n();
  const { enabled, user, can, logout } = useAuth();
  const isActive = (href: string) => {
    if (href === "/graph") return pathname === href;
    if (href === "/research") {
      return pathname === href || (pathname.startsWith("/research/") && !pathname.startsWith("/research/new") && !pathname.startsWith("/research/runs"));
    }
    if (href === "/research/new") return pathname.startsWith("/research/new") || pathname.startsWith("/research/runs");
    return pathname === href || (href !== "/" && pathname.startsWith(href));
  };
  const pageClassName = [
    "page",
    pathname.startsWith("/documents") ? "document-page" : "",
    pathname === "/chat" ? "ai-chat-page" : "",
    pathname === "/graph" || pathname === "/graph/system" ? "graph-page" : "",
  ].filter(Boolean).join(" ");
  const groups = can("owner")
    ? [...navigationGroups, { key: "navAdministration", items: adminNavigation }]
    : navigationGroups;
  const allNavigation = groups.flatMap((group) => group.items);
  // Điện thoại: thanh dưới với các mục dùng nhiều nhất, mọi mục khác trong bảng "Thêm".
  const quickNavigation = ["/", "/research/new", "/research", "/ingestion"]
    .map((href) => allNavigation.find((item) => item.href === href))
    .filter((item): item is (typeof allNavigation)[number] => Boolean(item));
  const sheetRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (sheetRef.current?.open) sheetRef.current.close();
  }, [pathname]);
  const activeNavigation = allNavigation.find((item) => isActive(item.href))
    ?? (pathname.startsWith("/account") ? { href: "/account", key: "account", icon: "members" as IconName } : navigation[0]);

  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">{t("skipToContent")}</a>
      <header className="topbar">
        <Link href="/" className="topbar-brand" aria-label={t("researchSystemHome")}>
          <span className="brand-logo" aria-hidden="true">✦</span>
          <span className="brand-name">
            Hệ thống nghiên cứu
            <small>{t("workspaceLabel")}</small>
          </span>
        </Link>

        <nav className="topnav" aria-label={t("workspace")}>
          {groups.map((group) => (
            <div className="topnav-group" key={group.key}>
              <span className="topnav-group-label">{t(group.key)}</span>
              {group.items.map((item) => (
                <Link
                  className={`topnav-link ${isActive(item.href) ? "current" : ""}`}
                  key={item.href}
                  href={item.href}
                  aria-label={t(item.key)}
                  title={t(item.key)}
                >
                  <span className="topnav-icon" aria-hidden="true"><NavIcon name={item.icon} /></span>
                  <span>{t(item.key)}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>

        <div className="topbar-actions">
          <ThemeToggle />
          {can("researcher") && <Link href="/ingestion" className="topbar-cta"><span aria-hidden="true">+</span>{t("addSources")}</Link>}
          {user && <div className="identity-menu" title={`${t("signedInAs")} ${user.email}`}>
            <span className="workspace-avatar">{user.name.slice(0, 1).toUpperCase()}</span>
            <Link className="identity-copy" href="/account" title={t("account")}><strong>{user.name}</strong><small>{t(`role${user.role[0].toUpperCase()}${user.role.slice(1)}`)}</small></Link>
            {enabled && <button className="identity-logout" onClick={() => void logout()}>{t("signOut")}</button>}
          </div>}
        </div>
      </header>

      <nav className="mobile-nav" aria-label={t("workspace")}>
        {allNavigation.map((item) => (
          <Link className={isActive(item.href) ? "current" : ""} key={item.href} href={item.href}>
            <NavIcon name={item.icon} />
            <span>{t(item.key)}</span>
          </Link>
        ))}
      </nav>

      <nav className="bottom-nav" aria-label="Điều hướng nhanh">
        {quickNavigation.map((item) => (
          <Link
            className={isActive(item.href) ? "current" : ""}
            aria-current={isActive(item.href) ? "page" : undefined}
            key={item.href}
            href={item.href}
          >
            <NavIcon name={item.icon} />
            <span>{t(item.key)}</span>
          </Link>
        ))}
        <button type="button" className="bottom-nav-more" aria-haspopup="dialog" onClick={() => sheetRef.current?.showModal?.()}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
          <span>Thêm</span>
        </button>
      </nav>
      <dialog className="nav-sheet" ref={sheetRef} aria-label="Tất cả mục điều hướng">
        <div className="nav-sheet-header">
          <strong>Tất cả mục</strong>
          <button type="button" className="secondary" onClick={() => sheetRef.current?.close()}>Đóng</button>
        </div>
        <nav aria-label="Tất cả mục">
          {allNavigation.map((item) => (
            <Link
              className={isActive(item.href) ? "current" : ""}
              aria-current={isActive(item.href) ? "page" : undefined}
              key={item.href}
              href={item.href}
              onClick={() => sheetRef.current?.close()}
            >
              <NavIcon name={item.icon} />
              <span>{t(item.key)}</span>
            </Link>
          ))}
        </nav>
      </dialog>

      <div className="main">
        <div className="workspace-bar">
          <div className="workspace-location">
            <span>{t("workspaceLabel")}</span>
            <strong>{t(activeNavigation.key)}</strong>
          </div>
          <div className="workspace-tools">
            <span className="workspace-status"><i aria-hidden="true" />{t("systemReady")}</span>
            <Link className="workspace-search" href="/search"><NavIcon name="search" /><span>{t("searchWorkspace")}</span></Link>
          </div>
        </div>
        <main className={pageClassName} id="main-content">{children}</main>
      </div>

      <footer className="site-footer">
        <div className="site-footer-inner">
          <Link href="/" className="site-footer-name" aria-label={t("researchSystemHome")}>
            Hệ thống nghiên cứu
          </Link>
          <nav className="site-footer-links" aria-label={t("workspace")}>
            <Link href="/research">{t("research")}</Link>
            <Link href="/ingestion">{t("sources")}</Link>
            <Link href="/graph">{t("graph")}</Link>
          </nav>
          <span className="site-footer-copyright">© {new Date().getFullYear()} Hệ thống nghiên cứu</span>
        </div>
      </footer>
    </div>
  );
}
