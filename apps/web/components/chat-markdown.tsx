/* eslint-disable @next/next/no-img-element -- imported signed asset URLs have no stable dimensions or loader contract */
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage } from "@/lib/types";

const allowedImageSuffixes = [
  "oaiusercontent.com",
  "oaistatic.com",
  "chatgpt.com",
  "openai.com",
];
const allowedImageHosts = new Set(["oaidalleapiprodscus.blob.core.windows.net"]);
const localChatImagePattern = /^\/api\/v1\/chat\/messages\/[A-Za-z0-9-]+\/media\/\d+$/;

export function isAllowedChatImageUrl(value: unknown): value is string {
  if (typeof value !== "string" || !value) return false;
  if (localChatImagePattern.test(value)) return true;
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
    return parsed.protocol === "https:"
      && !parsed.port
      && (allowedImageHosts.has(host)
        || allowedImageSuffixes.some((suffix) => host === suffix || host.endsWith(`.${suffix}`)));
  } catch {
    return false;
  }
}

function isSafeLink(value: string | undefined): value is string {
  if (!value) return false;
  if (value.startsWith("/") && !value.startsWith("//")) return true;
  try {
    return ["http:", "https:", "mailto:"].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}

const components: Components = {
  a: ({ href, children }) => isSafeLink(href)
    ? <a href={href} target={href.startsWith("/") ? undefined : "_blank"} rel="noreferrer">{children}</a>
    : <span>{children}</span>,
  img: ({ src, alt }) => isAllowedChatImageUrl(src)
    ? <img src={src} alt={alt ?? ""} loading="lazy" referrerPolicy="no-referrer" />
    : null,
};

export function ChatMarkdown({ content }: { content: string }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components} skipHtml>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function ChatMedia({ media }: { media: ChatMessage["media"] }) {
  const images = media.filter((item) => (
    item.type === "image" && isAllowedChatImageUrl(item.url)
  ));
  if (images.length === 0) return null;
  return (
    <div className="chat-media-grid">
      {images.map((item, index) => (
        <a href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${index}`}>
          <img
            src={item.url}
            alt={item.alt}
            loading="lazy"
            referrerPolicy="no-referrer"
          />
        </a>
      ))}
    </div>
  );
}
