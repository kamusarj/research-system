import { cookies } from "next/headers";
import { loadChatBootstrap } from "@/lib/chat-bootstrap";
import ChatWorkspace from "./chat-workspace";
import { ChatMarkdown } from "@/components/chat-markdown";
import { MESSAGE_WINDOW } from "@/lib/chat-window";

export const dynamic = "force-dynamic";

export default async function ChatPage() {
  const cookie = (await cookies()).toString();
  const target = (process.env.API_PROXY_TARGET || "http://localhost:8000").replace(/\/$/, "");
  const initial = await loadChatBootstrap(cookie, target);
  const renderedMessages = Object.fromEntries((initial?.messages ?? []).slice(-MESSAGE_WINDOW)
    .filter((message) => !message.error_code)
    .map((message) => [message.id, <ChatMarkdown key={message.id} content={message.content} />]));
  return <>
    <ChatWorkspace initial={initial} renderedMessages={renderedMessages} />
    {initial?.selectedId && <script dangerouslySetInnerHTML={{ __html:
      "{const e=document.getElementById('chat-message-list');if(e)e.scrollTop=e.scrollHeight;}" }} />}
  </>;
}
