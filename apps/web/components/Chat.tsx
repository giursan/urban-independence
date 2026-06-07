"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import { CrisisBanner } from "./CrisisBanner";

const CRISIS_RE = /\b(kill myself|killing myself|want to die|end my life|suicid|hurt myself|harm myself)\b/i;

export function Chat({ greeting }: { greeting: string }) {
  const conversationId = useMemo(
    () => (typeof crypto !== "undefined" ? crypto.randomUUID() : String(Date.now())),
    [],
  );
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

  const { messages, sendMessage, status, error } = useChat({ transport });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const busy = status === "submitted" || status === "streaming";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    if (CRISIS_RE.test(text)) setCrisis(true);
    sendMessage({ text });
    setInput("");
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-5">
      {crisis ? <CrisisBanner onDismiss={() => setCrisis(false)} /> : null}

      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="flex flex-1 flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-4"
      >
        {messages.length === 0 ? (
          <p className="m-auto max-w-md text-center text-xl leading-relaxed text-muted">
            {greeting}
          </p>
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
                  "max-w-[85%] whitespace-pre-wrap rounded-2xl px-5 py-3 text-xl leading-relaxed " +
                  (isUser
                    ? "bg-primary text-primary-foreground"
                    : "bg-background text-foreground")
                }
              >
                {text}
              </div>
            </div>
          );
        })}

        {busy ? (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-background px-5 py-3 text-xl text-muted">
              Thinking…
            </div>
          </div>
        ) : null}

        {error ? (
          <p className="text-lg text-danger">
            Sorry, something went wrong reaching your companion. Please try again.
          </p>
        ) : null}

        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="flex items-end gap-3">
        <label htmlFor="message" className="sr-only">
          Type your message
        </label>
        <textarea
          id="message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
          rows={2}
          placeholder="Type your message…"
          className="flex-1 resize-none rounded-2xl border border-border bg-card px-5 py-4 text-xl leading-relaxed shadow-sm focus:border-primary"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-2xl bg-primary px-7 py-4 text-xl font-bold text-primary-foreground shadow-sm disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
