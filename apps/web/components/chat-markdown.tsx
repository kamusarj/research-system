/* eslint-disable @next/next/no-img-element -- imported signed asset URLs have no stable dimensions or loader contract */
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { isAllowedChatImageUrl, isSafeLink } from "@/lib/chat-content-urls";
export { isAllowedChatImageUrl, isSafeLink } from "@/lib/chat-content-urls";
export { ChatMedia } from "./chat-media";

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
