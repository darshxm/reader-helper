"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import SendIcon from "@mui/icons-material/Send";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import CloseIcon from "@mui/icons-material/Close";
import type { Message } from "@/lib/storage";

interface Props {
  history: Message[];
  onSend: (text: string, imageBase64?: string) => void;
  streaming: boolean;
  streamingText: string;
  status: string;
  pendingImage: string | null;
  onClearImage: () => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}

const quickActions = [
  {
    label: "Simpler",
    prompt:
      "Please explain that in even simpler terms. Pretend I'm a complete beginner with no background in this topic. Use everyday language and simple analogies.",
  },
  {
    label: "Example",
    prompt:
      "Can you give me a concrete, real-world example of this concept? Something I might encounter in everyday life.",
  },
  {
    label: "Why important",
    prompt:
      "Why is this concept important? What problems does it solve or what would happen without it?",
  },
];

export default function ChatPanel({
  history,
  onSend,
  streaming,
  streamingText,
  status,
  pendingImage,
  onClearImage,
  inputRef,
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, streamingText]);

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

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", bgcolor: "background.paper" }}>
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SmartToyOutlinedIcon fontSize="small" color="primary" />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            AI Reading Assistant
          </Typography>
        </Box>
        {status && (
          <Typography variant="caption" color="text.secondary">
            {status}
          </Typography>
        )}
      </Box>

      {/* Messages */}
      <Box sx={{ flex: 1, overflowY: "auto", px: 2, py: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
        {history.length === 0 && !streaming && (
          <Typography
            variant="body2"
            color="text.disabled"
            sx={{ textAlign: "center", mt: 6, px: 2 }}
          >
            Open a PDF and start asking questions, or select text to explain it.
          </Typography>
        )}

        {history.map((msg, i) => (
          <Box
            key={i}
            sx={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}
          >
            <Paper
              elevation={0}
              sx={{
                px: 2,
                py: 1.25,
                maxWidth: "88%",
                fontSize: 14,
                lineHeight: 1.6,
                bgcolor:
                  msg.role === "user"
                    ? "primary.dark"
                    : "background.default",
                borderRadius:
                  msg.role === "user"
                    ? "16px 16px 4px 16px"
                    : "16px 16px 16px 4px",
                color: "text.primary",
              }}
            >
              {msg.role === "assistant" ? (
                <Box className="chat-message" sx={{ "& > *:first-of-type": { mt: 0 }, "& > *:last-child": { mb: 0 } }}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </Box>
              ) : (
                <>
                  {msg.content.includes("[image attached]") && (
                    <Typography variant="caption" sx={{ opacity: 0.7, display: "block", mb: 0.5 }}>
                      🖼 image attached
                    </Typography>
                  )}
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                    {msg.content}
                  </Typography>
                </>
              )}
            </Paper>
          </Box>
        ))}

        {/* Streaming */}
        {streaming && (
          <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
            <Paper
              elevation={0}
              sx={{
                px: 2,
                py: 1.25,
                maxWidth: "88%",
                fontSize: 14,
                bgcolor: "background.default",
                borderRadius: "16px 16px 16px 4px",
                color: "text.primary",
              }}
            >
              <Box className="chat-message" sx={{ "& > *:first-of-type": { mt: 0 }, "& > *:last-child": { mb: 0 } }}>
                <ReactMarkdown>{streamingText || "…"}</ReactMarkdown>
              </Box>
            </Paper>
          </Box>
        )}

        <div ref={bottomRef} />
      </Box>

      {/* Quick actions */}
      <Box data-tour="quick-actions" sx={{ px: 2, py: 1, display: "flex", gap: 1, borderTop: "1px solid", borderColor: "divider" }}>
        {quickActions.map((btn) => (
          <Button
            key={btn.label}
            size="small"
            variant="outlined"
            disabled={streaming || history.length === 0}
            onClick={() => onSend(btn.prompt)}
            sx={{ flex: 1, fontSize: 12, borderColor: "divider", color: "text.secondary", "&:hover": { borderColor: "primary.main", color: "primary.main" } }}
          >
            {btn.label}
          </Button>
        ))}
      </Box>

      {/* Pending image preview */}
      {pendingImage && (
        <>
          <Divider />
          <Box sx={{ px: 2, py: 1, display: "flex", alignItems: "center", gap: 1 }}>
            <Box
              component="img"
              src={`data:image/png;base64,${pendingImage}`}
              alt="attachment"
              sx={{ maxHeight: 60, maxWidth: 120, objectFit: "contain", borderRadius: 1, border: "1px solid", borderColor: "divider" }}
            />
            <IconButton size="small" onClick={onClearImage} sx={{ color: "text.secondary" }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </>
      )}

      {/* Input */}
      <Box data-tour="chat-input" sx={{ px: 2, py: 1.5, borderTop: "1px solid", borderColor: "divider", display: "flex", gap: 1, alignItems: "flex-end" }}>
        <TextField
          inputRef={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask a question…"
          multiline
          maxRows={4}
          disabled={streaming}
          fullWidth
          size="small"
          variant="outlined"
        />
        <IconButton
          onClick={handleSend}
          disabled={streaming || (!input.trim() && !pendingImage)}
          color="primary"
          sx={{ mb: 0.25 }}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
}
