"use client";

import { useCallback, useRef, useState } from "react";
import { saveConversation, type Message } from "./storage";

interface Options {
  fileName: string | null;
  pdfHash: string | null;
  model: string;
  apiKey: string;
  onQuotaExhausted?: () => void;
}

export function useGeminiChat(
  { fileName, pdfHash, model, apiKey, onQuotaExhausted }: Options,
  history: Message[],
  setHistory: (msgs: Message[]) => void,
) {
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [status, setStatus] = useState("");
  const [freeRemaining, setFreeRemaining] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Stable ref so onQuotaExhausted never needs to be in the dependency array
  const onQuotaExhaustedRef = useRef(onQuotaExhausted);
  onQuotaExhaustedRef.current = onQuotaExhausted;

  const sendMessage = useCallback(
    async (text: string, imageBase64?: string) => {
      if (!fileName) return;
      if (streaming) {
        abortRef.current?.abort();
      }

      const userMsg: Message = {
        role: "user",
        content: text || "Please explain what is shown in this image.",
      };
      const newHistory = [...history, userMsg];
      setHistory(newHistory);
      if (pdfHash) saveConversation(pdfHash, newHistory);

      setStreaming(true);
      setStreamingText("");
      setStatus("Thinking…");

      abortRef.current = new AbortController();

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // Only send Authorization header when the user has their own key
            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
          },
          body: JSON.stringify({
            message: text,
            model,
            fileName,
            history: newHistory,
            imageBase64,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: res.statusText }));
          if (err.code === "QUOTA_EXHAUSTED") {
            onQuotaExhaustedRef.current?.();
          }
          throw new Error(err.error ?? "Request failed");
        }

        // Read free-tier remaining count from response header (present only on free tier)
        const remaining = res.headers.get("x-free-remaining");
        if (remaining !== null) {
          setFreeRemaining(parseInt(remaining, 10));
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const lines = decoder.decode(value).split("\n");
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.error) throw new Error(parsed.error);
              if (parsed.text) {
                fullText += parsed.text;
                setStreamingText(fullText);
              }
            } catch (parseErr) {
              if ((parseErr as Error).message !== "Unexpected end of JSON input") {
                throw parseErr;
              }
            }
          }
        }

        const assistantMsg: Message = { role: "assistant", content: fullText };
        const finalHistory = [...newHistory, assistantMsg];
        setHistory(finalHistory);
        if (pdfHash) saveConversation(pdfHash, finalHistory);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          const errMsg: Message = {
            role: "assistant",
            content: "❌ Error: " + (err as Error).message,
          };
          setHistory([...newHistory, errMsg]);
          if (pdfHash) saveConversation(pdfHash, [...newHistory, errMsg]);
        }
      } finally {
        setStreaming(false);
        setStreamingText("");
        setStatus("");
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fileName, streaming, history, pdfHash, model, apiKey, setHistory],
  );

  return { sendMessage, streaming, streamingText, status, freeRemaining };
}
