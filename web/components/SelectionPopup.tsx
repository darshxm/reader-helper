"use client";

import { useEffect, useRef } from "react";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

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

  const label =
    hasText && hasImage ? "Explain text & image" : hasImage ? "Explain image" : "Explain this";

  return (
    <Paper
      ref={ref}
      elevation={6}
      sx={{
        position: "fixed",
        left: x,
        top: y - 52,
        zIndex: 1200,
        transform: "translateX(-50%)",
        borderRadius: 5,
        overflow: "hidden",
      }}
    >
      <Button
        onClick={() => { onExplain(); onClose(); }}
        variant="contained"
        size="small"
        startIcon={<AutoAwesomeIcon sx={{ fontSize: "16px !important" }} />}
        sx={{ px: 2, py: 1, whiteSpace: "nowrap", borderRadius: 5 }}
      >
        {label}
      </Button>
    </Paper>
  );
}
