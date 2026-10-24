import { describe, expect, it } from "vitest";
import { detectSourceKind, isActiveSubmission, parseTranscript, parseUrls } from "./intake";

describe("intake utilities", () => {
  it("parses one URL per line and removes duplicates", () => {
    expect(parseUrls("https://example.com/a\n\nhttps://example.com/b\nhttps://example.com/a")).toEqual([
      "https://example.com/a",
      "https://example.com/b",
    ]);
  });

  it("detects source families before submission", () => {
    expect(detectSourceKind("https://github.com/openai/codex/issues/1")).toBe("github");
    expect(detectSourceKind("https://fb.watch/example")).toBe("facebook");
    expect(detectSourceKind("https://arxiv.org/pdf/2601.00001")).toBe("paper");
    expect(detectSourceKind("https://example.com/report.pdf?download=1")).toBe("pdf");
    expect(detectSourceKind("https://example.com/article")).toBe("article");
    expect(detectSourceKind("not a url")).toBe("invalid");
  });

  it("polls only while pipeline jobs are active", () => {
    expect(isActiveSubmission("fetching")).toBe(true);
    expect(isActiveSubmission("partial_success")).toBe(false);
    expect(isActiveSubmission("failed")).toBe(false);
  });

  it("parses and validates ordered transcript timestamps", () => {
    expect(parseTranscript("00:12 Opening\n01:02 Evidence\n75 Final note")).toEqual([
      { timestamp_seconds: 12, text: "Opening" },
      { timestamp_seconds: 62, text: "Evidence" },
      { timestamp_seconds: 75, text: "Final note" },
    ]);
    expect(() => parseTranscript("01:00 Sau\n00:10 Trước")).toThrow(/đúng thứ tự/);
    expect(() => parseTranscript("thiếu mốc thời gian")).toThrow(/Mốc thời gian không hợp lệ/);
  });
});
