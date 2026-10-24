import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./app-shell";

const mocks = vi.hoisted(() => ({ pathname: "/research" }));

vi.mock("next/navigation", () => ({ usePathname: () => mocks.pathname }));
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    enabled: false,
    user: { name: "Local owner", email: "local@research.system", role: "owner" },
    can: () => true,
    logout: vi.fn(),
  }),
}));
vi.mock("@/lib/i18n", () => {
  const labels: Record<string, string> = {
    workspaceLabel: "Research workspace",
    navLibrary: "Research workflow",
    navIntelligence: "Knowledge tools",
    systemReady: "System ready",
    searchWorkspace: "Search library",
    skipToContent: "Skip to content",
    researchSystemHome: "Research System home",
    dashboard: "Dashboard",
    research: "Research",
    researchLibrary: "Research library",
    documentWorkspace: "Document workspace",
    sources: "Sources",
    search: "Search",
    graph: "Knowledge graph",
    graphChanges: "Graph changes",
    brainstormChat: "Brainstorm chat",
    gaps: "Knowledge gaps",
    collector: "Collector",
    addSources: "Add sources",
    language: "Language",
    workspace: "Research intelligence workspace",
    signedInAs: "Signed in as",
    roleOwner: "Owner",
  };
  return {
    useI18n: () => ({
      locale: "vi",
      t: (key: string) => labels[key] ?? key,
    }),
  };
});

describe("AppShell footer", () => {
  beforeEach(() => {
    mocks.pathname = "/research";
  });

  it("renders one compact footer with only the core navigation", () => {
    render(<AppShell><h1>Page content</h1></AppShell>);

    expect(screen.getByRole("main")).toHaveTextContent("Page content");
    const footer = screen.getByRole("contentinfo");
    expect(screen.getAllByRole("contentinfo")).toHaveLength(1);
    expect(within(footer).getByRole("link", { name: "Research System home" })).toHaveAttribute("href", "/");
    const navigation = within(footer).getByRole("navigation", { name: "Research intelligence workspace" });
    expect(within(navigation).getAllByRole("link")).toHaveLength(3);
    expect(within(navigation).getByRole("link", { name: "Research" })).toHaveAttribute("href", "/research");
    expect(within(navigation).getByRole("link", { name: "Sources" })).toHaveAttribute("href", "/ingestion");
    expect(within(navigation).getByRole("link", { name: "Knowledge graph" })).toHaveAttribute("href", "/graph");
    expect(footer).toHaveTextContent(`© ${new Date().getFullYear()} Hệ thống nghiên cứu`);
  });

  it("shows the renamed document workspace in primary navigation", () => {
    render(<AppShell><h1>Page content</h1></AppShell>);

    expect(screen.getAllByRole("link", { name: "Document workspace" })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: "Documents" })).not.toBeInTheDocument();
  });

  it("groups the desktop navigation and exposes the active workspace context", () => {
    render(<AppShell><h1>Page content</h1></AppShell>);

    expect(screen.getByText("Research workflow")).toBeInTheDocument();
    expect(screen.getByText("Knowledge tools")).toBeInTheDocument();
    expect(screen.getByText("System ready")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Search library" })).toHaveAttribute("href", "/search");
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute("href", "#main-content");
  });

  it("removes the shared reading-width cap from both graph canvas routes", () => {
    mocks.pathname = "/graph";
    const { rerender } = render(<AppShell><h1>Graph</h1></AppShell>);

    expect(screen.getByRole("main")).toHaveClass("page", "graph-page");

    mocks.pathname = "/graph/system";
    rerender(<AppShell><h1>System graph</h1></AppShell>);
    expect(screen.getByRole("main")).toHaveClass("page", "graph-page");

    mocks.pathname = "/graph/changes";
    rerender(<AppShell><h1>Changes</h1></AppShell>);
    expect(screen.getByRole("main")).not.toHaveClass("graph-page");
  });
});

describe("AppShell mobile bottom navigation", () => {
  it("offers the four most used destinations plus a sheet with everything else", () => {
    mocks.pathname = "/research/runs/abc";
    render(<AppShell><h1>Run</h1></AppShell>);
    const bottom = screen.getByRole("navigation", { name: "Điều hướng nhanh" });
    const links = within(bottom).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual(["/", "/research/new", "/research", "/ingestion"]);
    expect(within(bottom).getByRole("link", { name: "deepResearchNav" })).toHaveAttribute("aria-current", "page");
    expect(within(bottom).getByRole("link", { name: "Research" })).not.toHaveAttribute("aria-current");
    expect(within(bottom).getByRole("button", { name: "Thêm" })).toHaveAttribute("aria-haspopup", "dialog");
  });
});
