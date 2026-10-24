import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SubmissionError } from "./submission-error";
import { LocaleProvider } from "@/lib/i18n";

describe("SubmissionError", () => {
  it("explains a known code and says what to do next", () => {
    render(
      <LocaleProvider>
        <SubmissionError
          code="ACCESS_DENIED"
          message="Access to the source was denied"
          details={{ status_code: 403 }}
        />
      </LocaleProvider>,
    );

    expect(screen.getByText("Trang web từ chối yêu cầu")).toBeInTheDocument();
    expect(screen.getByText(/Nhà xuất bản chặn trình đọc tự động/)).toBeInTheDocument();
    expect(screen.getByText("ACCESS_DENIED")).toBeInTheDocument();
    expect(screen.getByText(/HTTP 403/)).toBeInTheDocument();
  });

  it("uses a safe Vietnamese fallback for an unknown code", () => {
    render(
      <LocaleProvider>
        <SubmissionError code="SOME_FUTURE_CODE" message="A newer server said this" />
      </LocaleProvider>,
    );

    expect(screen.getByText("Không thể xử lý nguồn này")).toBeInTheDocument();
    expect(screen.queryByText("A newer server said this")).not.toBeInTheDocument();
    expect(screen.queryByText(/errorHint\./)).not.toBeInTheDocument();
  });

  it("renders nothing when there is no failure", () => {
    const { container } = render(
      <LocaleProvider>
        <SubmissionError code={null} message={null} />
      </LocaleProvider>,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
