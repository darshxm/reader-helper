"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "@/components/ChatPanel";
import NotesPanel from "@/components/NotesPanel";
import SelectionPopup from "@/components/SelectionPopup";
import ApiKeyGate from "@/components/ApiKeyGate";
import { hashFile } from "@/lib/hash";
import {
  loadConversation,
  saveConversation,
  loadLastPage,
  loadPreference,
  savePreference,
  loadApiKey,
  saveApiKey,
  clearApiKey,
  type Message,
} from "@/lib/storage";
import { AVAILABLE_MODELS, DEFAULT_MODEL } from "@/lib/gemini";

const PDFViewer = dynamic(() => import("@/components/PDFViewer"), { ssr: false });

interface SelectionState {
  text: string;
  imageBase64: string | null;
  x: number;
  y: number;
}

export default function Home() {
  // API key
  const [apiKey, setApiKey] = useState<string>("");
  const [keyLoaded, setKeyLoaded] = useState(false);

  useEffect(() => {
    setApiKey(loadApiKey());
    setKeyLoaded(true);
  }, []);

  function handleSaveKey(key: string) {
    saveApiKey(key);
    setApiKey(key);
  }

  function handleRemoveKey() {
    clearApiKey();
    setApiKey("");
  }

  // PDF state
  const [fileBytes, setFileBytes] = useState<Uint8Array | null>(null);
  const [pdfHash, setPdfHash] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState<string>("");
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState<number>(() => loadPreference("zoom", 1.5));
  const [uploading, setUploading] = useState(false);

  // Chat state
  const [history, setHistory] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [status, setStatus] = useState("");
  const [model, setModel] = useState<string>(() => loadPreference("model", DEFAULT_MODEL));

  // Selection popup
  const [selection, setSelection] = useState<SelectionState | null>(null);
  const [pendingImage, setPendingImage] = useState<string | null>(null);

  // Tabs
  const [activeTab, setActiveTab] = useState<"chat" | "notes">("chat");

  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ── Auth header helper ────────────────────────────────────────────────────

  function authHeaders(): Record<string, string> {
    return { Authorization: `Bearer ${apiKey}` };
  }

  // ── File open ─────────────────────────────────────────────────────────────

  const MAX_PDF_MB = 4;
  const MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024;

  async function handleFileOpen(file: File) {
    if (file.size > MAX_PDF_BYTES) {
      alert(`This PDF is ${(file.size / 1024 / 1024).toFixed(1)} MB. The maximum supported size is ${MAX_PDF_MB} MB.`);
      return;
    }
    setUploading(true);
    setStatus("Reading file…");
    setPdfName(file.name);
    setFileName(null);

    const bytes = new Uint8Array(await file.arrayBuffer());
    setFileBytes(bytes);

    setStatus("Computing hash…");
    const hash = await hashFile(file);
    setPdfHash(hash);

    const lastPage = loadLastPage(hash);
    setCurrentPage(lastPage);
    const savedHistory = loadConversation(hash);
    setHistory(savedHistory);

    // Check KV cache
    setStatus("Checking upload cache…");
    let geminiFileName: string | null = null;

    try {
      const res = await fetch(`/api/upload?hash=${hash}`);
      const data = await res.json();
      if (data.fileName) {
        geminiFileName = data.fileName;
        setStatus("Using cached upload ✓");
      }
    } catch {
      // ignore
    }

    if (!geminiFileName) {
      setStatus("Uploading to Gemini…");
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("hash", hash);
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: authHeaders(),
          body: form,
        });
        const data = await res.json();
        if (data.error) {
          setStatus(`Upload failed: ${data.error}`);
        } else {
          geminiFileName = data.fileName ?? null;
          setStatus(geminiFileName ? "Uploaded ✓" : "Upload failed — AI features disabled");
        }
      } catch {
        setStatus("Upload failed — AI features disabled");
      }
    }

    setFileName(geminiFileName);
    setUploading(false);
    setTimeout(() => setStatus(""), 3000);

    const welcomeMsg: Message = savedHistory.length > 0
      ? {
          role: "assistant",
          content: `📄 Reopened **${file.name}**\n\nYour previous conversation has been restored.`,
        }
      : {
          role: "assistant",
          content: `📄 Loaded **${file.name}**\n\nI'm ready to help you understand this document. You can:\n- Select any text or region and click **Explain this**\n- Ask me questions in the chat\n- Use the quick action buttons below`,
        };

    const newHistory = [...savedHistory, welcomeMsg];
    setHistory(newHistory);
    saveConversation(hash, newHistory);
  }

  function onFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFileOpen(file);
    e.target.value = "";
  }

  // ── Chat ──────────────────────────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string, imageBase64?: string) => {
    if (!fileName) {
      alert("Please open a PDF first.");
      return;
    }
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
    setPendingImage(null);

    abortRef.current = new AbortController();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ message: text, model, fileName, history: newHistory, imageBase64 }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error ?? "Request failed");
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileName, streaming, history, pdfHash, model, apiKey]);

  // ── Selection popup ───────────────────────────────────────────────────────

  function onSelection(info: { text: string; imageBase64: string | null; x: number; y: number }) {
    if (!info.text && !info.imageBase64) return;
    setSelection(info);
  }

  function onExplain() {
    if (!selection) return;
    const { text, imageBase64 } = selection;
    let prompt = "";
    if (text && imageBase64) {
      prompt = `Please explain this text and image:\n\n${text}`;
    } else if (imageBase64) {
      prompt = "What is shown in this image? Please explain any diagrams, charts, or visual elements.";
    } else {
      prompt = `Please explain this text in simple terms:\n\n${text}`;
    }
    if (imageBase64) setPendingImage(imageBase64);
    if (inputRef.current) {
      inputRef.current.value = prompt;
      inputRef.current.focus();
    }
    setActiveTab("chat");
  }

  // ── Render ────────────────────────────────────────────────────────────────

  // Wait until localStorage is read before deciding whether to show the gate
  if (!keyLoaded) return null;

  return (
    <div className="flex flex-col h-screen" style={{ background: "#1a1a1a" }}>
      {/* API key gate — shown as overlay when no key is set */}
      {!apiKey && <ApiKeyGate onSave={handleSaveKey} />}

      {/* Toolbar */}
      <div
        className="flex items-center gap-4 px-4 py-2 flex-shrink-0"
        style={{ background: "#2d2d2d", borderBottom: "1px solid #444" }}
      >
        <label className="cursor-pointer">
          <input type="file" accept=".pdf" className="hidden" onChange={onFileInput} />
          <span
            className="px-3 py-1.5 rounded text-sm cursor-pointer"
            style={{ background: "#3d3d3d", color: "#e0e0e0", border: "1px solid #555" }}
          >
            📂 Open PDF
          </span>
        </label>
        <span className="text-xs" style={{ color: "#666" }}>Max 4 MB</span>

        {pdfName && (
          <span className="text-sm truncate max-w-xs" style={{ color: "#999" }}>
            {pdfName}
          </span>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-sm" style={{ color: "#999" }}>Zoom:</span>
          <input
            type="range" min={50} max={300}
            value={Math.round(zoom * 100)}
            onChange={(e) => { const v = Number(e.target.value) / 100; setZoom(v); savePreference("zoom", v); }}
            className="w-24"
          />
          <span className="text-sm w-10" style={{ color: "#e0e0e0" }}>{Math.round(zoom * 100)}%</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: "#999" }}>Model:</span>
          <select
            value={model}
            onChange={(e) => { setModel(e.target.value); savePreference("model", e.target.value); }}
            className="text-sm rounded px-2 py-1"
            style={{ background: "#3d3d3d", color: "#e0e0e0", border: "1px solid #555", outline: "none" }}
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        {/* Key management */}
        <button
          onClick={handleRemoveKey}
          title="Remove API key"
          className="text-xs px-2 py-1 rounded"
          style={{ background: "#3d3d3d", color: "#999", border: "1px solid #555" }}
        >
          🔑 Remove key
        </button>

        {uploading && (
          <span className="text-sm" style={{ color: "#4a9eff" }}>{status}</span>
        )}
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {/* PDF panel */}
        <div className="flex flex-col" style={{ width: "60%", borderRight: "1px solid #444" }}>
          {fileBytes ? (
            <PDFViewer
              fileBytes={fileBytes}
              pdfHash={pdfHash}
              onSelection={onSelection}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
              totalPages={totalPages}
              onTotalPages={setTotalPages}
              zoom={zoom}
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4" style={{ color: "#555" }}>
              <div style={{ fontSize: 64 }}>📄</div>
              <div style={{ fontSize: 18 }}>Open a PDF to get started</div>
              <label className="cursor-pointer">
                <input type="file" accept=".pdf" className="hidden" onChange={onFileInput} />
                <span
                  className="px-6 py-3 rounded-lg text-sm font-medium cursor-pointer"
                  style={{ background: "#4a9eff", color: "#fff" }}
                >
                  Choose PDF
                </span>
              </label>
              <span style={{ color: "#555", fontSize: 13 }}>Max 4 MB per file</span>
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <div className="flex" style={{ background: "#2d2d2d", borderBottom: "1px solid #444" }}>
            {(["chat", "notes"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className="px-6 py-3 text-sm font-medium"
                style={{
                  background: activeTab === tab ? "#252525" : "transparent",
                  color: activeTab === tab ? "#4a9eff" : "#999",
                  border: "none",
                  borderBottom: activeTab === tab ? "2px solid #4a9eff" : "2px solid transparent",
                  cursor: "pointer",
                }}
              >
                {tab === "chat" ? "💬 Chat" : "📝 Notes"}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            <div style={{ display: activeTab === "chat" ? "flex" : "none", flexDirection: "column", height: "100%" }}>
              <ChatPanel
                history={history}
                onSend={sendMessage}
                streaming={streaming}
                streamingText={streamingText}
                status={!uploading ? status : ""}
                pendingImage={pendingImage}
                onClearImage={() => setPendingImage(null)}
                onSetInput={() => {}}
                inputRef={inputRef}
              />
            </div>
            <div style={{ display: activeTab === "notes" ? "flex" : "none", flexDirection: "column", height: "100%" }}>
              <NotesPanel pdfHash={pdfHash} />
            </div>
          </div>
        </div>
      </div>

      {selection && (
        <SelectionPopup
          x={selection.x}
          y={selection.y}
          hasText={!!selection.text}
          hasImage={!!selection.imageBase64}
          onExplain={onExplain}
          onClose={() => setSelection(null)}
        />
      )}
    </div>
  );
}
