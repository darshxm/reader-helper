"use client";

import { useState } from "react";

interface Props {
  onSave: (key: string) => void;
}

export default function ApiKeyGate({ onSave }: Props) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed.startsWith("AIza")) {
      setError("Gemini API keys start with 'AIza'. Check your key and try again.");
      return;
    }
    onSave(trimmed);
  }

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: "rgba(0,0,0,0.85)" }}
    >
      <div
        className="rounded-xl p-8 w-full max-w-md"
        style={{ background: "#2d2d2d", border: "1px solid #444" }}
      >
        <h2 className="text-xl font-semibold mb-2" style={{ color: "#fff" }}>
          Enter your Gemini API key
        </h2>
        <p className="text-sm mb-1" style={{ color: "#999" }}>
          This app uses your own Google Gemini API key. It is stored only in your browser and sent
          directly to Gemini over HTTPS — never stored on any server.
        </p>
        <a
          href="https://aistudio.google.com/app/apikey"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm underline block mb-6"
          style={{ color: "#4a9eff" }}
        >
          Get a free API key from Google AI Studio →
        </a>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="password"
            value={value}
            onChange={(e) => { setValue(e.target.value); setError(""); }}
            placeholder="AIzaSy..."
            autoFocus
            className="rounded px-3 py-2 text-sm"
            style={{
              background: "#1a1a1a",
              color: "#e0e0e0",
              border: "1px solid #555",
              outline: "none",
            }}
          />
          {error && <p className="text-sm" style={{ color: "#ff6b6b" }}>{error}</p>}
          <button
            type="submit"
            disabled={!value.trim()}
            className="rounded py-2 text-sm font-medium disabled:opacity-40"
            style={{ background: "#4a9eff", color: "#fff" }}
          >
            Save &amp; continue
          </button>
        </form>

        <p className="text-xs mt-4" style={{ color: "#666" }}>
          Your key is saved in localStorage and cleared if you click "Remove key" in the toolbar.
        </p>
      </div>
    </div>
  );
}
