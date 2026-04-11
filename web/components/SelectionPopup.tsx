"use client";

import { useEffect, useRef } from "react";

interface Props {
  x: number;
  y: number;
  hasText: boolean;
  hasImage: boolean;
  onExplain: () => void;
  onClose: () => void;
}

export default function SelectionPopup({ x, y, hasText, hasImage, onExplain, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const label = hasText && hasImage
    ? "🤖 Explain text & image"
    : hasImage
    ? "🤖 Explain image"
    : "🤖 Explain this";

  return (
    <div
      ref={ref}
      style={{
        position: "fixed",
        left: x,
        top: y - 50,
        zIndex: 1000,
        transform: "translateX(-50%)",
      }}
    >
      <button
        onClick={() => { onExplain(); onClose(); }}
        className="px-4 py-2 rounded-lg text-sm font-medium shadow-lg"
        style={{
          background: "#4a9eff",
          color: "#fff",
          border: "none",
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </button>
    </div>
  );
}
