"use client";

import { type UIMessage } from "@ai-sdk/react";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Chat } from "./Chat";

type Conversation = {
  id: string;
  mode?: string;
  started_at: string;
  last_message?: string | null;
  last_role?: "user" | "assistant" | "system" | null;
  last_message_at?: string | null;
};

type StoredMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
};

function newConversationId() {
  return typeof crypto !== "undefined" ? crypto.randomUUID() : String(Date.now());
}

function toUiMessage(message: StoredMessage): UIMessage {
  return {
    id: message.id,
    role: message.role,
    parts: [{ type: "text", text: message.content }],
  };
}

function dateLabel(value?: string | null) {
  if (!value) return "New session";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function sessionLabel(conversation: Conversation) {
  if (conversation.mode === "phone") return "Phone call";
  const text = conversation.last_message?.trim();
  if (!text) return "New conversation";
  return text.length > 56 ? `${text.slice(0, 56)}...` : text;
}

export function ConversationWorkspace({ greeting }: { greeting: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState(() => newConversationId());
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState("");

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId) ?? null,
    [activeId, conversations],
  );

  async function loadConversations(preferredId?: string) {
    setLoadingConversations(true);
    setError("");
    try {
      const res = await apiFetch("/conversations");
      if (!res.ok) throw new Error("Could not load sessions.");
      const rows = (await res.json()) as Conversation[];
      setConversations(rows);
      if (preferredId) return;
      if (rows.length) setActiveId(rows[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sessions.");
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadMessages(conversationId: string) {
    if (!conversations.some((conversation) => conversation.id === conversationId)) {
      setMessages([]);
      return;
    }
    setLoadingMessages(true);
    setError("");
    try {
      const res = await apiFetch(`/conversations/${conversationId}/messages`);
      if (!res.ok) throw new Error("Could not load this session.");
      const rows = (await res.json()) as StoredMessage[];
      setMessages(rows.map(toUiMessage));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this session.");
    } finally {
      setLoadingMessages(false);
    }
  }

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    loadMessages(activeId);
  }, [activeId, conversations]);

  function startNewConversation() {
    setActiveId(newConversationId());
    setMessages([]);
    setError("");
  }

  async function deleteConversation(conversationId: string) {
    const conversation = conversations.find((item) => item.id === conversationId);
    const label = conversation ? sessionLabel(conversation) : "this session";
    if (!window.confirm(`Delete "${label}"?`)) return;

    setError("");
    const res = await apiFetch(`/conversations/${conversationId}`, { method: "DELETE" });
    if (!res.ok) {
      setError("Could not delete that session.");
      return;
    }

    const remaining = conversations.filter((item) => item.id !== conversationId);
    setConversations(remaining);
    if (activeId === conversationId) {
      if (remaining.length) setActiveId(remaining[0].id);
      else startNewConversation();
    }
  }

  async function refreshAfterActivity() {
    await loadConversations(activeId);
  }

  return (
    <main className="mx-auto grid w-full max-w-6xl flex-1 gap-4 px-4 py-5 lg:grid-cols-[19rem_minmax(0,1fr)]">
      <aside className="rounded-2xl border border-border bg-card p-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Sessions</h1>
          <button
            type="button"
            onClick={startNewConversation}
            className="rounded-lg bg-primary px-4 py-2 text-base font-semibold text-primary-foreground"
          >
            New
          </button>
        </div>

        {error ? <p className="mt-3 text-base text-danger">{error}</p> : null}

        <div className="mt-4 space-y-2">
          {loadingConversations ? (
            <p className="text-base text-muted">Loading sessions...</p>
          ) : conversations.length === 0 ? (
            <p className="text-base leading-relaxed text-muted">No saved sessions yet.</p>
          ) : (
            conversations.map((conversation) => {
              const active = conversation.id === activeId;
              return (
                <div
                  key={conversation.id}
                  className={
                    "rounded-xl border p-3 " +
                    (active ? "border-primary bg-background" : "border-border bg-card")
                  }
                >
                  <button
                    type="button"
                    onClick={() => setActiveId(conversation.id)}
                    className="block w-full text-left"
                  >
                    <span className="block text-base font-semibold">
                      {dateLabel(conversation.last_message_at ?? conversation.started_at)}
                    </span>
                    <span className="mt-1 block overflow-hidden text-ellipsis whitespace-nowrap text-base text-muted">
                      {conversation.last_role === "user" ? "You: " : ""}
                      {sessionLabel(conversation)}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteConversation(conversation.id)}
                    className="mt-2 rounded-lg border border-border px-3 py-1 text-sm font-semibold text-muted hover:bg-background"
                  >
                    Delete
                  </button>
                </div>
              );
            })
          )}
        </div>
      </aside>

      <section className="flex min-h-[70vh] min-w-0 flex-col rounded-2xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <p className="text-lg font-semibold">
            {activeConversation ? dateLabel(activeConversation.last_message_at) : "New conversation"}
          </p>
          <p className="text-base text-muted">
            {activeConversation?.mode === "phone" ? "Started by phone call" : "Adaptive companion chat"}
          </p>
        </div>

        {loadingMessages ? (
          <p className="m-auto text-lg text-muted">Loading this session...</p>
        ) : (
          <Chat
            key={activeId}
            greeting={greeting}
            conversationId={activeId}
            initialMessages={messages}
            onActivity={refreshAfterActivity}
          />
        )}
      </section>
    </main>
  );
}
