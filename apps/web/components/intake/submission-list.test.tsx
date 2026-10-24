import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SubmissionList } from "./submission-list";
import type { SourceSubmission } from "@/lib/types";

const base: SourceSubmission = {
  id: "source-1",
  url: "https://example.com/report.pdf",
  source_type: "manual",
  status: "partial_success",
  stage: "completed",
  review_status: "needs_review",
  title: "Scanned report",
  content_preview: "",
  classification: {
    summary: "Public metadata",
    normalized_source: {
      source_type: "pdf",
      collection_status: "PARTIAL",
      limitation_code: "PDF_NO_TEXT_LAYER",
      limitation_message: "The PDF has no readable text layer.",
    },
  },
  transcript: { configured: false, language: null, segment_count: 0, updated_at: null },
  provider_name: "mistral",
  model_name: null,
  attempt_count: 1,
  next_attempt_at: null,
  error: null,
  error_code: null,
  error_details: {},
  research_id: null,
  created_at: "2026-07-15T00:00:00Z",
  updated_at: "2026-07-15T00:01:00Z",
};

describe("SubmissionList", () => {
  it("renders loading and empty states", () => {
    const { rerender } = render(
      <SubmissionList items={[]} loading error={null} onAction={vi.fn()} />,
    );
    expect(screen.getByText("loading")).toBeInTheDocument();
    rerender(<SubmissionList items={[]} loading={false} error={null} onAction={vi.fn()} />);
    expect(screen.getByText("noLinks")).toBeInTheDocument();
  });

  it("shows partial-success limitations and review actions", () => {
    render(<SubmissionList items={[base]} loading={false} error={null} onAction={vi.fn()} />);
    expect(screen.getAllByText("status.partial_success")).toHaveLength(2);
    expect(screen.getByText("unknownLimitation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "approve" })).toBeInTheDocument();
  });

  it("shows typed errors and retries only the failed row", async () => {
    const onAction = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionList
        items={[{ ...base, status: "failed", review_status: "not_requested", error: "Timed out", error_code: "FETCH_TIMEOUT" }]}
        loading={false}
        error={null}
        onAction={onAction}
      />,
    );
    expect(screen.getByText(/FETCH_TIMEOUT/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "retry" }));
    await waitFor(() => expect(onAction).toHaveBeenCalledWith("source-1", "retry"));
  });

  it("renders query errors without hiding the table", () => {
    render(
      <SubmissionList items={[base]} loading={false} error="API unavailable" onAction={vi.fn()} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("API unavailable");
    expect(screen.getByText("Scanned report")).toBeInTheDocument();
  });

  it("accepts a timestamped transcript for a Facebook Reel", async () => {
    const onTranscript = vi.fn().mockResolvedValue(undefined);
    const reel: SourceSubmission = {
      ...base,
      url: "https://www.facebook.com/reel/123",
      title: "Public Reel",
      classification: {
        normalized_source: {
          source_type: "facebook",
          collection_status: "PARTIAL",
          limitation_code: "TRANSCRIPT_UNAVAILABLE",
          limitation_message: "Transcript unavailable.",
          metadata: { resource_kind: "reel" },
        },
      },
    };
    render(
      <SubmissionList
        items={[reel]}
        loading={false}
        error={null}
        onAction={vi.fn()}
        onTranscript={onTranscript}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "addTranscript" }));
    fireEvent.change(screen.getByPlaceholderText("00:12 Nội dung transcript"), {
      target: { value: "00:12 Grounded opening\n01:02 Human review evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: "saveTranscript" }));
    await waitFor(() => expect(onTranscript).toHaveBeenCalledWith(
      "source-1",
      "vi",
      [
        { timestamp_seconds: 12, text: "Grounded opening" },
        { timestamp_seconds: 62, text: "Human review evidence" },
      ],
    ));
  });
});
