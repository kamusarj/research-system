import { api } from "@/lib/api";
import type {
  ChatMessage,
  ChatScopeType,
  ChatSession,
  ChatSessionList,
  ChatTurn,
} from "@/lib/types";

export function listChatSessions(): Promise<ChatSessionList> {
  return api("/chat/sessions");
}

export function listPersonalChatModels(provider: string, apiKey: string, signal?: AbortSignal): Promise<{ provider: string; models: string[] }> {
  return api("/chat/connections/models", {
    method: "POST", signal, cache: "no-store",
    body: JSON.stringify({ provider, personal_api_key: apiKey }),
  });
}

export function verifyPersonalChatModel(provider: string, apiKey: string, model: string, signal?: AbortSignal): Promise<{ provider: string; model_name: string; verified: true }> {
  return api("/chat/connections/verify", {
    method: "POST", signal, cache: "no-store",
    body: JSON.stringify({ provider, personal_api_key: apiKey, model_name: model }),
  });
}

export type ChatConnectionRequest = {
  credential_source?: "system" | "personal";
  model_name?: string;
  personal_api_key?: string;
};

export function createChatSession(request: ChatConnectionRequest & {
  title?: string;
  scope_type: ChatScopeType;
  scope_id?: string;
  provider: string;
}): Promise<ChatSession> {
  return api("/chat/sessions", { method: "POST", body: JSON.stringify(request) });
}

export function importChatGPTSharedChat(request: ChatConnectionRequest & {
  url: string;
  provider: string;
}): Promise<ChatSession> {
  return api("/chat/imports/chatgpt", { method: "POST", body: JSON.stringify(request) });
}

export function listChatMessages(sessionId: string): Promise<ChatMessage[]> {
  return api(`/chat/sessions/${sessionId}/messages`);
}

export function sendChatMessage(sessionId: string, content: string, personalApiKey?: string): Promise<ChatTurn> {
  return api(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, ...(personalApiKey ? { personal_api_key: personalApiKey } : {}) }),
  });
}

export function closeChatSession(sessionId: string): Promise<ChatSession> {
  return api(`/chat/sessions/${sessionId}/close`, { method: "POST" });
}

export function summarizeChatSession(sessionId: string): Promise<ChatSession> {
  return api(`/chat/sessions/${sessionId}/summarize`, {
    method: "POST",
    body: JSON.stringify({ summary: null }),
  });
}
