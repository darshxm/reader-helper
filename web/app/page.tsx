"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Alert from "@mui/material/Alert";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import KeyIcon from "@mui/icons-material/Key";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
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
import { useGeminiChat } from "@/lib/useGeminiChat";

const PDFViewer = dynamic(() => import("@/components/PDFViewer"), { ssr: false });

interface SelectionState {
  text: string;
  imageBase64: string | null;
  x: number;
  y: number;
}

export default function Home() {
  // API key
  const [apiKey, setApiKey] = useState("");
  const [keyLoaded, setKeyLoaded] = useState(false);

  // Free tier
  const [freeTierAvailable, setFreeTierAvailable] = useState(false);
  const [freeTierLoaded, setFreeTierLoaded] = useState(false);
  const [initialFreeRemaining, setInitialFreeRemaining] = useState<number | null>(null);
  const [quotaExhausted, setQuotaExhausted] = useState(false);

  useEffect(() => {
    setApiKey(loadApiKey());
    setKeyLoaded(true);
  }, []);

  // Fetch free tier status once we know there's no personal key
  useEffect(() => {
    if (!keyLoaded) return;
    if (apiKey) {
      setFreeTierLoaded(true);
      return;
    }
    fetch("/api/quota")
      .then((r) => r.json())
      .then((data) => {
        setFreeTierAvailable(data.available);
        setInitialFreeRemaining(data.remaining ?? null);
      })
      .catch(() => setFreeTierAvailable(false))
      .finally(() => setFreeTierLoaded(true));
  }, [keyLoaded, apiKey]);

  function handleSaveKey(key: string) {
    saveApiKey(key);
    setApiKey(key);
    setQuotaExhausted(false);
  }

  function handleRemoveKey() {
    clearApiKey();
    setApiKey("");
    setQuotaExhausted(false);
  }

  // PDF state
  const [fileBytes, setFileBytes] = useState<Uint8Array | null>(null);
  const [pdfHash, setPdfHash] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState<number>(() => loadPreference("zoom", 1.5));
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Chat state
  const [history, setHistory] = useState<Message[]>([]);
  const [model, setModel] = useState<string>(() => loadPreference("model", DEFAULT_MODEL));

  const { sendMessage, streaming, streamingText, status: chatStatus, freeRemaining } =
    useGeminiChat(
      {
        fileName,
        pdfHash,
        model,
        apiKey,
        onQuotaExhausted: () => setQuotaExhausted(true),
      },
      history,
      setHistory,
    );

  // Selection popup
  const [selection, setSelection] = useState<SelectionState | null>(null);
  const [pendingImage, setPendingImage] = useState<string | null>(null);

  // Tabs
  const [activeTab, setActiveTab] = useState(0);

  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!errorMsg) return;
    const t = setTimeout(() => setErrorMsg(""), 4000);
    return () => clearTimeout(t);
  }, [errorMsg]);

  // ── File open ─────────────────────────────────────────────────────────────

  const MAX_PDF_MB = 4;
  const MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024;

  async function handleFileOpen(file: File) {
    if (file.size > MAX_PDF_BYTES) {
      setErrorMsg(`PDF is ${(file.size / 1024 / 1024).toFixed(1)} MB — maximum is ${MAX_PDF_MB} MB.`);
      return;
    }
    setUploading(true);
    setUploadStatus("Reading file…");
    setPdfName(file.name);
    setFileName(null);

    const bytes = new Uint8Array(await file.arrayBuffer());
    setFileBytes(bytes);

    setUploadStatus("Computing hash…");
    const hash = await hashFile(file);
    setPdfHash(hash);

    setCurrentPage(loadLastPage(hash));
    const savedHistory = loadConversation(hash);
    setHistory(savedHistory);

    setUploadStatus("Checking upload cache…");
    let geminiFileName: string | null = null;

    try {
      const res = await fetch(`/api/upload?hash=${hash}`);
      const data = await res.json();
      if (data.fileName) {
        geminiFileName = data.fileName;
        setUploadStatus("Using cached upload ✓");
      }
    } catch {
      // ignore
    }

    if (!geminiFileName) {
      setUploadStatus("Uploading to Gemini…");
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("hash", hash);
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
          body: form,
        });
        const data = await res.json();
        if (data.error) {
          setUploadStatus(`Upload failed: ${data.error}`);
        } else {
          geminiFileName = data.fileName ?? null;
          setUploadStatus(geminiFileName ? "Uploaded ✓" : "Upload failed — AI features disabled");
        }
      } catch {
        setUploadStatus("Upload failed — AI features disabled");
      }
    }

    setFileName(geminiFileName);
    setUploading(false);
    setTimeout(() => setUploadStatus(""), 3000);

    const welcomeMsg: Message =
      savedHistory.length > 0
        ? { role: "assistant", content: `📄 Reopened **${file.name}**\n\nYour previous conversation has been restored.` }
        : { role: "assistant", content: `📄 Loaded **${file.name}**\n\nI'm ready to help you understand this document. You can:\n- Select any text or region and click **Explain this**\n- Ask me questions in the chat\n- Use the quick action buttons below` };

    const newHistory = [...savedHistory, welcomeMsg];
    setHistory(newHistory);
    saveConversation(hash, newHistory);
  }

  function onFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFileOpen(file);
    e.target.value = "";
  }

  // ── Send wrapper ──────────────────────────────────────────────────────────

  function handleSend(text: string, imageBase64?: string) {
    if (!fileName) {
      setErrorMsg("Please open a PDF first.");
      return;
    }
    setPendingImage(null);
    sendMessage(text, imageBase64);
  }

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
    setActiveTab(0);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  // Wait for both localStorage and free-tier status before rendering
  if (!keyLoaded || !freeTierLoaded) return null;

  // Show gate when: no personal key AND (free tier unavailable OR quota exhausted)
  const showKeyGate = !apiKey && (!freeTierAvailable || quotaExhausted);

  // Free messages remaining: prefer live count from hook, fall back to initial fetch
  const displayFreeRemaining = freeRemaining ?? initialFreeRemaining;
  const onFreeTier = !apiKey && freeTierAvailable;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", bgcolor: "background.default" }}>
      {showKeyGate && <ApiKeyGate onSave={handleSaveKey} quotaExhausted={quotaExhausted} />}

      {/* Toolbar */}
      <AppBar
        position="static"
        elevation={0}
        sx={{ bgcolor: "background.paper", borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Toolbar variant="dense" sx={{ gap: 1.5, minHeight: 48 }}>
          <Button
            component="label"
            variant="outlined"
            size="small"
            startIcon={<FolderOpenIcon />}
            sx={{ flexShrink: 0 }}
          >
            Open PDF
            <input type="file" accept=".pdf" hidden onChange={onFileInput} />
          </Button>

          <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
            Max 4 MB
          </Typography>

          {pdfName && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, overflow: "hidden" }}>
              <PictureAsPdfIcon sx={{ fontSize: 14, color: "text.secondary", flexShrink: 0 }} />
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 220 }}
              >
                {pdfName}
              </Typography>
            </Box>
          )}

          {errorMsg && (
            <Alert severity="error" sx={{ py: 0, px: 1.5, fontSize: 13, flexShrink: 0 }}>
              {errorMsg}
            </Alert>
          )}

          {uploading && (
            <Typography variant="caption" color="primary" sx={{ flexShrink: 0 }}>
              {uploadStatus}
            </Typography>
          )}

          <Box sx={{ flex: 1 }} />

          {/* Free tier counter */}
          {onFreeTier && displayFreeRemaining !== null && (
            <Chip
              size="small"
              label={`${displayFreeRemaining} free ${displayFreeRemaining === 1 ? "message" : "messages"} left`}
              color={displayFreeRemaining <= 2 ? "warning" : "default"}
              variant="outlined"
              sx={{ fontSize: 12 }}
            />
          )}

          {/* Zoom */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexShrink: 0 }}>
            <Typography variant="caption" color="text.secondary">Zoom</Typography>
            <Slider
              value={Math.round(zoom * 100)}
              min={50}
              max={300}
              onChange={(_, v) => {
                const val = (v as number) / 100;
                setZoom(val);
                savePreference("zoom", val);
              }}
              sx={{ width: 80 }}
              size="small"
            />
            <Typography variant="caption" color="text.primary" sx={{ width: 36, textAlign: "right" }}>
              {Math.round(zoom * 100)}%
            </Typography>
          </Box>

          {/* Model */}
          <Select
            value={model}
            onChange={(e) => { setModel(e.target.value); savePreference("model", e.target.value); }}
            size="small"
            variant="outlined"
            sx={{ fontSize: 13, height: 32, minWidth: 180 }}
          >
            {AVAILABLE_MODELS.map((m) => (
              <MenuItem key={m} value={m} sx={{ fontSize: 13 }}>{m}</MenuItem>
            ))}
          </Select>

          {apiKey ? (
            <Tooltip title="Remove API key">
              <IconButton size="small" onClick={handleRemoveKey} sx={{ color: "text.secondary" }}>
                <KeyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : (
            <Tooltip title="Add your own API key">
              <Button
                size="small"
                variant="text"
                startIcon={<KeyIcon fontSize="small" />}
                onClick={() => setQuotaExhausted(true)} // reuse gate as entry point
                sx={{ color: "text.secondary", fontSize: 12 }}
              >
                Add key
              </Button>
            </Tooltip>
          )}
        </Toolbar>
      </AppBar>

      {/* Main area */}
      <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* PDF panel */}
        <Box sx={{ width: "60%", display: "flex", flexDirection: "column", borderRight: "1px solid", borderColor: "divider" }}>
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
            <Box
              sx={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 2, color: "text.disabled" }}
            >
              <PictureAsPdfIcon sx={{ fontSize: 72, opacity: 0.3 }} />
              <Typography variant="h6" color="text.disabled">Open a PDF to get started</Typography>
              <Button component="label" variant="contained" size="large">
                Choose PDF
                <input type="file" accept=".pdf" hidden onChange={onFileInput} />
              </Button>
              <Typography variant="caption" color="text.disabled">Max 4 MB per file</Typography>
            </Box>
          )}
        </Box>

        {/* Right panel */}
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            sx={{ minHeight: 44, borderBottom: "1px solid", borderColor: "divider", bgcolor: "background.paper", "& .MuiTabs-indicator": { height: 2 } }}
          >
            <Tab label="Chat" />
            <Tab label="Notes" />
          </Tabs>

          <Box sx={{ flex: 1, overflow: "hidden" }}>
            <Box sx={{ display: activeTab === 0 ? "flex" : "none", flexDirection: "column", height: "100%" }}>
              <ChatPanel
                history={history}
                onSend={handleSend}
                streaming={streaming}
                streamingText={streamingText}
                status={chatStatus}
                pendingImage={pendingImage}
                onClearImage={() => setPendingImage(null)}
                inputRef={inputRef}
              />
            </Box>
            <Box sx={{ display: activeTab === 1 ? "flex" : "none", flexDirection: "column", height: "100%" }}>
              <NotesPanel pdfHash={pdfHash} />
            </Box>
          </Box>
        </Box>
      </Box>

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
    </Box>
  );
}
