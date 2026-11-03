import type { ChatMessage, ChatSessionList, Provider } from "@/lib/types";
import { MESSAGE_WINDOW } from "@/lib/chat-window";

export type ChatBootstrap = {
  userId: string;
  sessions: ChatSessionList;
  providers: Provider[];
  selectedId: string | null;
  messages: ChatMessage[];
  messageTotal?: number;
};

// Called only by the server route. Every request forwards the current session;
// private results are never cached or shared between page requests.
export async function loadChatBootstrap(cookie: string, target: string): Promise<ChatBootstrap | undefined> {
  async function read<T>(path: string): Promise<T> {
    const response = await fetch(`${target}/api/v1${path}`, {
      headers: { Cookie: cookie }, cache: "no-store", signal: AbortSignal.timeout(4000),
    });
    if (!response.ok) throw new Error("Chat bootstrap unavailable");
    return response.json() as Promise<T>;
  }
  try {
    const me = await read<{ enabled: boolean; user: { id: string } }>("/auth/me");
    if (me.enabled !== true || !me.user?.id) return undefined;
    const [sessions, providers] = await Promise.all([
      read<ChatSessionList>("/chat/sessions"), read<Provider[]>("/ai/providers"),
    ]);
    const selectedId = sessions.items[0]?.id ?? null;
    const messages = selectedId
      ? await read<ChatMessage[]>(`/chat/sessions/${encodeURIComponent(selectedId)}/messages`)
      : [];
    return { userId: me.user.id, sessions, providers, selectedId,
      messages: messages.slice(-MESSAGE_WINDOW), messageTotal: messages.length };
  } catch {
    // Login, provider errors and unavailable services retain the existing client recovery flow.
    return undefined;
  }
}
