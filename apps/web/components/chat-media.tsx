/* eslint-disable @next/next/no-img-element -- imported signed URLs have no stable loader contract */
import type { ChatMessage } from "@/lib/types";
import { isAllowedChatImageUrl } from "@/lib/chat-content-urls";

export function ChatMedia({ media }: { media: ChatMessage["media"] }) {
  const images = media.filter((item) => item.type === "image" && isAllowedChatImageUrl(item.url));
  if (!images.length) return null;
  return <div className="chat-media-grid">{images.map((item, index) => (
    <a href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${index}`}>
      <img src={item.url} alt={item.alt} loading="lazy" referrerPolicy="no-referrer" />
    </a>
  ))}</div>;
}
