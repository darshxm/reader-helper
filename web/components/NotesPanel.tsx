"use client";

import { useEffect, useState, useRef } from "react";
import { loadNotes, saveNotes } from "@/lib/storage";

interface Props {
  pdfHash: string | null;
}

export default function NotesPanel({ pdfHash }: Props) {
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (pdfHash) {
      setNotes(loadNotes(pdfHash));
    } else {
      setNotes("");
    }
  }, [pdfHash]);

  function handleChange(value: string) {
    setNotes(value);
    setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      if (pdfHash) {
        saveNotes(pdfHash, value);
        setSaved(true);
      }
    }, 500);
  }

  return (
    <div className="flex flex-col h-full" style={{ background: "#252525" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid #444" }}>
        <span style={{ color: "#e0e0e0", fontWeight: 600 }}>📝 Document Notes</span>
        {saved && <span style={{ color: "#4caf50", fontSize: 12 }}>✓ Saved</span>}
      </div>
      <textarea
        value={notes}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={pdfHash ? "Take notes about this document…" : "Open a PDF to start taking notes."}
        disabled={!pdfHash}
        className="flex-1 p-4 text-sm resize-none disabled:opacity-50"
        style={{
          background: "transparent",
          color: "#e0e0e0",
          border: "none",
          outline: "none",
          lineHeight: 1.6,
        }}
      />
    </div>
  );
}
