import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProviderStatus } from "./provider-status";
import { LocaleProvider } from "@/lib/i18n";
import type { Provider } from "@/lib/types";

const provider = (overrides: Partial<Provider> & { id: string }): Provider => ({
  configured: true,
  reachable: null,
  active: false,
  chat_active: false,
  model: "some-model",
  ...overrides,
});

function renderStatus(providers: Provider[], onPreflight = vi.fn().mockResolvedValue(undefined)) {
  return render(
    <LocaleProvider>
      <ProviderStatus providers={providers} onPreflight={onPreflight} />
    </LocaleProvider>,
  );
}

describe("ProviderStatus", () => {
  it("distinguishes not-yet-checked from not-answering", () => {
    renderStatus([
      provider({ id: "deepseek" }),
      provider({ id: "ollama", reachable: false }),
      provider({ id: "mistral", reachable: true }),
    ]);

    expect(screen.getByTestId("provider-deepseek")).toHaveTextContent("chưa kiểm tra");
    expect(screen.getByTestId("provider-ollama")).toHaveTextContent("không phản hồi");
    expect(screen.getByTestId("provider-mistral")).toHaveTextContent("đang phản hồi");
  });

  it("explains the cost of an unreachable provider", () => {
    renderStatus([provider({ id: "openai", reachable: false })]);

    expect(screen.getByText(/làm bước phân loại thất bại sau khi nguồn đã được tải về/))
      .toBeInTheDocument();
  });

  it("stays quiet when no provider is configured", () => {
    const { container } = renderStatus([provider({ id: "gemini", configured: false })]);

    expect(container).toBeEmptyDOMElement();
  });

  it("runs the preflight on request", async () => {
    const onPreflight = vi.fn().mockResolvedValue(undefined);
    renderStatus([provider({ id: "deepseek" })], onPreflight);

    fireEvent.click(screen.getByText("Kiểm tra ngay"));

    await waitFor(() => expect(onPreflight).toHaveBeenCalled());
  });

  it("reports a failed preflight rather than appearing to succeed", async () => {
    const onPreflight = vi.fn().mockRejectedValue(new Error("Preflight route is down"));
    renderStatus([provider({ id: "deepseek" })], onPreflight);

    fireEvent.click(screen.getByText("Kiểm tra ngay"));

    expect(await screen.findByRole("alert")).toHaveTextContent("Preflight route is down");
  });
});
