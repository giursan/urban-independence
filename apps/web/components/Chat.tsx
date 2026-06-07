"use client";

import { type UIMessage, useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import { CrisisBanner } from "./CrisisBanner";

const CRISIS_RE = /\b(kill myself|killing myself|want to die|end my life|suicid|hurt myself|harm myself)\b/i;

export function Chat({
  greeting,
  conversationId,
  initialMessages = [],
  onActivity,
}: {
  greeting: string;
  conversationId: string;
  initialMessages?: UIMessage[];
  onActivity?: () => void;
}) {
  const [crisis, setCrisis] = useState(false);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${API_BASE}/chat`,
        body: () => ({ conversation_id: conversationId }),
      }),
    [conversationId],
  );

  const { messages, sendMessage, status, error } = useChat({
    id: conversationId,
    messages: initialMessages,
    transport,
    onFinish: () => onActivity?.(),
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const busy = status === "submitted" || status === "streaming";
  const hasMessages = messages.length > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    if (CRISIS_RE.test(text)) setCrisis(true);
    sendMessage({ text });
    setInput("");
  }

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-4 px-3 pb-4 pt-3 sm:px-5 sm:pb-5">
      {crisis ? <CrisisBanner onDismiss={() => setCrisis(false)} /> : null}

      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto rounded-2xl bg-card p-3 sm:p-5"
      >
        {!hasMessages ? (
          <div className="m-auto flex max-w-xl flex-col items-center gap-4 px-2 py-12 text-center">
            <div>
              <p className="text-2xl font-semibold leading-snug text-foreground">{greeting}</p>
              <p className="mt-3 text-lg leading-relaxed text-muted">
                Write a message below. Short notes are perfectly fine.
              </p>
            </div>
          </div>
        ) : null}

        {messages.map((message) => {
          const isUser = message.role === "user";
          const text = message.parts
            .map((p) => (p.type === "text" ? p.text : ""))
            .join("");
          if (!text) return null;
          return (
            <div
              key={message.id}
              className={isUser ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  "max-w-[88%] whitespace-pre-wrap rounded-2xl px-5 py-4 text-xl leading-relaxed sm:max-w-[78%] " +
                  (isUser
                    ? "rounded-br-md bg-foreground text-white"
                    : "rounded-bl-md bg-background text-foreground")
                }
              >
                <span
                  className={
                    "mb-1 block text-sm font-bold uppercase tracking-wide " +
                    (isUser ? "text-white/75" : "text-muted")
                  }
                >
                  {isUser ? "You" : "Companion"}
                </span>
                {text}
              </div>
            </div>
          );
        })}

        {busy ? (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md bg-background px-5 py-4 text-xl text-muted">
              <span className="mb-1 block text-sm font-bold uppercase tracking-wide text-muted">
                Companion
              </span>
              Thinking...
            </div>
          </div>
        ) : null}

        {error ? (
          <p className="rounded-xl border border-danger bg-white px-4 py-3 text-lg font-semibold text-danger">
            Sorry, something went wrong reaching your companion. Please try again.
          </p>
        ) : null}

        <div ref={endRef} />
      </div>

      <form
        onSubmit={submit}
        className="rounded-2xl border border-border bg-card p-3 sm:p-4"
      >
        <label htmlFor="message" className="sr-only">
          Type your message
        </label>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <textarea
            id="message"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) submit(e);
            }}
            rows={2}
            placeholder="Type your message..."
            className="min-h-28 flex-1 resize-none rounded-xl border border-border bg-white px-5 py-4 text-xl leading-relaxed focus:border-primary sm:min-h-24"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="min-h-16 rounded-xl bg-foreground px-8 py-4 text-2xl font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60 sm:min-w-36"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
