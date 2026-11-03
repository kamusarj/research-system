const suffixes = ["oaiusercontent.com", "oaistatic.com", "chatgpt.com", "openai.com"];
const hosts = new Set(["oaidalleapiprodscus.blob.core.windows.net"]);
const localImage = /^\/api\/v1\/chat\/messages\/[A-Za-z0-9-]+\/media\/\d+$/;

export function isAllowedChatImageUrl(value: unknown): value is string {
  if (typeof value !== "string" || !value) return false;
  if (localImage.test(value)) return true;
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
    return parsed.protocol === "https:" && !parsed.port
      && (hosts.has(host) || suffixes.some((suffix) => host === suffix || host.endsWith(`.${suffix}`)));
  } catch { return false; }
}

export function isSafeLink(value: string | undefined): value is string {
  if (!value) return false;
  if (value.startsWith("/") && !value.startsWith("//")) return true;
  try { return ["http:", "https:", "mailto:"].includes(new URL(value).protocol); }
  catch { return false; }
}
