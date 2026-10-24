import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReviewBacklog } from "./review-backlog";
import { LocaleProvider } from "@/lib/i18n";
import type { ReviewBacklog as Summary } from "@/lib/types";

const empty: Summary = {
  needs_review: 0,
  approved: 4,
  rejected: 1,
  duplicate: 0,
  not_requested: 0,
  failed: 0,
  duplicates_awaiting_original: 0,
  auto_approve_confidence: 0.85,
};

function renderBacklog(backlog: Summary | undefined, onBulkReview = vi.fn()) {
  return render(
    <LocaleProvider>
      <ReviewBacklog backlog={backlog} canApprove onBulkReview={onBulkReview} />
    </LocaleProvider>,
  );
}

describe("ReviewBacklog", () => {
  it("says how many sources are waiting and what that costs", () => {
    renderBacklog({ ...empty, needs_review: 24 });

    expect(
      screen.getByText("24 nguồn đã thu thập đang chờ quyết định"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Chỉ nguồn đã duyệt mới được đưa vào đồ thị tri thức/)).toBeInTheDocument();
    expect(screen.getByText(/trên 85%/)).toBeInTheDocument();
  });

  it("stays out of the way when there is nothing to decide", () => {
    const { container } = renderBacklog(empty);

    expect(container).toBeEmptyDOMElement();
  });

  it("surfaces duplicates that are stuck behind an unpublished original", () => {
    renderBacklog({ ...empty, needs_review: 2, duplicates_awaiting_original: 3 });

    expect(
      screen.getByText("3 bản trùng đang chờ bản gốc được xuất bản."),
    ).toBeInTheDocument();
  });

  it("decides the whole queue in one action", async () => {
    const onBulkReview = vi.fn().mockResolvedValue(undefined);
    renderBacklog({ ...empty, needs_review: 5 }, onBulkReview);

    fireEvent.click(screen.getByText("Duyệt toàn bộ hàng chờ"));

    await waitFor(() => expect(onBulkReview).toHaveBeenCalledWith("approve"));
  });

  it("reports a failed bulk decision instead of appearing to succeed", async () => {
    const onBulkReview = vi.fn().mockRejectedValue(new Error("Server refused the batch"));
    renderBacklog({ ...empty, needs_review: 5 }, onBulkReview);

    fireEvent.click(screen.getByText("Từ chối toàn bộ hàng chờ"));

    expect(await screen.findByRole("alert")).toHaveTextContent("Server refused the batch");
  });

  it("hides bulk actions from a reader who cannot approve", () => {
    render(
      <LocaleProvider>
        <ReviewBacklog
          backlog={{ ...empty, needs_review: 5 }}
          canApprove={false}
          onBulkReview={vi.fn()}
        />
      </LocaleProvider>,
    );

    expect(screen.queryByText("Duyệt toàn bộ hàng chờ")).not.toBeInTheDocument();
  });
});
