import type { SourceKind, TranscriptSegment } from "@/lib/types";

export type DetectedSourceKind = SourceKind | "invalid";

export function parseUrls(value: string): string[] {
  return [...new Set(value.split(/\r?\n/).map((url) => url.trim()).filter(Boolean))];
}

export function detectSourceKind(value: string): DetectedSourceKind {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) return "invalid";
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    const path = url.pathname.toLowerCase();
    if (host === "github.com") return "github";
    if (["facebook.com", "m.facebook.com", "fb.watch"].includes(host)) return "facebook";
    if (["arxiv.org", "doi.org", "dx.doi.org", "semanticscholar.org", "ieeexplore.ieee.org", "dl.acm.org", "link.springer.com", "sciencedirect.com"].includes(host)) return "paper";
    if (path.endsWith(".pdf")) return "pdf";
    return "article";
  } catch {
    return "invalid";
  }
}

export function isActiveSubmission(status: string): boolean {
  return ["pending", "processing", "fetching", "extracting", "analyzing"].includes(status);
}

function timestampSeconds(value: string): number {
  if (/^\d+(?:\.\d+)?$/.test(value)) return Number(value);
  const parts = value.split(":");
  if (parts.length < 2 || parts.length > 3 || parts.some((part) => !/^\d+$/.test(part))) {
    throw new Error(`Mốc thời gian không hợp lệ: ${value}`);
  }
  const [hours, minutes, seconds] = parts.length === 3 ? parts : ["0", ...parts];
  const result = Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds);
  if (Number(minutes) >= 60 || Number(seconds) >= 60) throw new Error(`Mốc thời gian không hợp lệ: ${value}`);
  return result;
}

export function parseTranscript(value: string): TranscriptSegment[] {
  const segments = value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line, index) => {
    const match = line.match(/^\[?([^\]\s]+)\]?\s+(.+)$/);
    if (!match) throw new Error(`Dòng ${index + 1} cần có mốc thời gian và nội dung`);
    return { timestamp_seconds: timestampSeconds(match[1]), text: match[2].trim() };
  });
  if (!segments.length) throw new Error("Hãy thêm ít nhất một đoạn chép lời");
  if (segments.length > 500) throw new Error("Bản chép lời vượt quá 500 đoạn");
  if (segments.some((segment, index) => index > 0 && segment.timestamp_seconds < segments[index - 1].timestamp_seconds)) {
    throw new Error("Các mốc thời gian trong bản chép lời phải theo đúng thứ tự");
  }
  if (segments.reduce((total, segment) => total + segment.text.length, 0) > 120_000) {
    throw new Error("Bản chép lời vượt quá 120.000 ký tự");
  }
  return segments;
}

/** Một phần liên kết bị từ chối; giữ lại đúng các URL đó để người dùng sửa và gửi lại. */
export class PartialIntakeError extends Error {
  constructor(message: string, public failedUrls: string[]) {
    super(message);
    this.name = "PartialIntakeError";
  }
}
