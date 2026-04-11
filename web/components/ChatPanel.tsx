"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/storage";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  imageBase64?: string;
}

interface Props {
  history: Message[];
  onSend: (text: string, imageBase64?: string) => void;
  streaming: boolean;
  streamingText: string;
  status: string;
  pendingImage: string | null;
  onClearImage: () => void;
  onSetInput: (text: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}

export default function ChatPanel({
  history,
  onSend,
  streaming,
  streamingText,
  status,
  pendingImage,
  onClearImage,
  onSetInput,
  inputRef,
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, streamingText]);

  // Expose setInput via onSetInput
  useEffect(() => {
    // nothing — parent calls onSetInput which sets state in parent; we sync via a ref pattern below
  }, []);

  function handleSend() {
    const text = input.trim();
    if (!text && !pendingImage) return;
    onSend(text, pendingImage ?? undefined);
    setInput("");
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const displayMessages: ChatMessage[] = history.map((m) => ({ role: m.role, content: m.content }));

  return (
    <div className="flex flex-col h-full" style={{ background: "#252525" }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid #444" }}>
        <span style={{ color: "#e0e0e0", fontWeight: 600 }}>🤖 AI Reading Assistant</span>
        {status && <span style={{ color: "#999", fontSize: 12 }}>{status}</span>}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {displayMessages.length === 0 && !streaming && (
          <div style={{ color: "#666", fontSize: 14, textAlign: "center", marginTop: 40 }}>
            Open a PDF and start asking questions, or select text to explain it.
          </div>
        )}

        {displayMessages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "user" ? (
              <div
                className="rounded-lg px-4 py-2 max-w-[85%] text-sm"
                style={{ background: "#1a4a7a", color: "#e0e0e0" }}
              >
                {msg.imageBase64 && (
                  <div className="mb-2 text-xs opacity-70">🖼️ [image attached]</div>
                )}
                <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
              </div>
            ) : (
              <div
                className="rounded-lg px-4 py-2 max-w-[95%] text-sm chat-message"
                style={{ background: "#2d2d2d", color: "#e0e0e0" }}
              >
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}

        {/* Streaming response */}
        {streaming && (
          <div className="flex justify-start">
            <div
              className="rounded-lg px-4 py-2 max-w-[95%] text-sm chat-message"
              style={{ background: "#2d2d2d", color: "#e0e0e0" }}
            >
              <ReactMarkdown>{streamingText || "…"}</ReactMarkdown>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick actions */}
      <div className="flex gap-2 px-4 py-2" style={{ borderTop: "1px solid #333" }}>
        {[
          { label: "🎯 Simpler", color: "#1a5c2a", prompt: "Please explain that in even simpler terms. Pretend I'm a complete beginner with no background in this topic. Use everyday language and simple analogies." },
          { label: "📝 Example", color: "#1a4a4a", prompt: "Can you give me a concrete, real-world example of this concept? Something I might encounter in everyday life." },
          { label: "❓ Why important", color: "#4a3a00", prompt: "Why is this concept important? What problems does it solve or what would happen without it?" },
        ].map((btn) => (
          <button
            key={btn.label}
            disabled={streaming || history.length === 0}
            onClick={() => onSend(btn.prompt)}
            className="text-xs px-3 py-1 rounded disabled:opacity-40 flex-1"
            style={{ background: btn.color, color: "#e0e0e0", border: "none" }}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Image preview */}
      {pendingImage && (
        <div className="px-4 py-2 flex items-center gap-2" style={{ borderTop: "1px solid #333" }}>
          <img
            src={`data:image/png;base64,${pendingImage}`}
            alt="attachment"
            className="rounded"
            style={{ maxHeight: 60, maxWidth: 120, objectFit: "contain", border: "1px solid #555" }}
          />
          <button onClick={onClearImage} style={{ color: "#999", fontSize: 18, background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3" style={{ borderTop: "1px solid #444" }}>
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              onSetInput(e.target.value);
            }}
            onKeyDown={handleKey}
            placeholder="Ask a question…"
            rows={2}
            disabled={streaming}
            className="flex-1 rounded px-3 py-2 text-sm resize-none disabled:opacity-50"
            style={{
              background: "#3d3d3d",
              color: "#e0e0e0",
              border: "1px solid #555",
              outline: "none",
            }}
          />
          <button
            onClick={handleSend}
            disabled={streaming || (!input.trim() && !pendingImage)}
            className="px-4 py-2 rounded text-sm font-medium disabled:opacity-40"
            style={{ background: "#1a4a7a", color: "#e0e0e0", minWidth: 60 }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
