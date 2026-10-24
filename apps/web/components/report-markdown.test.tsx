import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReportMarkdown } from "./report-markdown";

const REPORT = "## Thị trường\n\nAgent đã vào sản xuất. [1](https://a.example/x)[2](/research/abc)\n\nXem [trang chủ](https://b.example) và [lạ](javascript:alert(1)).\n\n<script>alert(1)</script>";

describe("ReportMarkdown", () => {
  it("renders numeric links as citation buttons that open the evidence panel", () => {
    const onCite = vi.fn();
    render(<ReportMarkdown content={REPORT} onCite={onCite} activeCitation={2} />);
    const first = screen.getByRole("link", { name: "Nguồn 1" });
    expect(first).toHaveClass("citation");
    expect(first).toHaveAttribute("href", "https://a.example/x");
    expect(first).toHaveAttribute("target", "_blank");
    fireEvent.click(first);
    expect(onCite).toHaveBeenCalledWith(1);
    const internal = screen.getByRole("link", { name: "Nguồn 2" });
    expect(internal).toHaveClass("active");
    expect(internal).not.toHaveAttribute("target");
  });

  it("keeps ordinary safe links and neutralizes unsafe links and raw HTML", () => {
    const { container } = render(<ReportMarkdown content={REPORT} />);
    expect(screen.getByRole("link", { name: "trang chủ" })).toHaveAttribute("href", "https://b.example");
    expect(screen.queryByRole("link", { name: "lạ" })).toBeNull();
    expect(screen.getByText("lạ")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });

  it("lets modified clicks open the source normally", () => {
    const onCite = vi.fn();
    render(<ReportMarkdown content={REPORT} onCite={onCite} />);
    fireEvent.click(screen.getByRole("link", { name: "Nguồn 1" }), { ctrlKey: true });
    expect(onCite).not.toHaveBeenCalled();
  });
});
