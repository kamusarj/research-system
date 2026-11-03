"use client";

import { useLayoutEffect } from "react";
import { ChatMarkdown } from "./chat-markdown";

export function ChatMarkdownClient({ content, onRendered }: { content: string; onRendered?: () => void }) {
  useLayoutEffect(() => { onRendered?.(); }, [content, onRendered]);
  return <ChatMarkdown content={content} />;
}
