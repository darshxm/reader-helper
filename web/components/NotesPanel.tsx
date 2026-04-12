"use client";

import { useEffect, useState, useRef } from "react";
import { loadNotes, saveNotes } from "@/lib/storage";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import EditNoteIcon from "@mui/icons-material/EditNote";
import CheckIcon from "@mui/icons-material/Check";

interface Props {
  pdfHash: string | null;
}

export default function NotesPanel({ pdfHash }: Props) {
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setNotes(pdfHash ? loadNotes(pdfHash) : "");
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
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", bgcolor: "background.paper" }}>
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
          <EditNoteIcon fontSize="small" color="primary" />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Document Notes
          </Typography>
        </Box>
        {saved && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <CheckIcon sx={{ fontSize: 14, color: "success.main" }} />
            <Typography variant="caption" color="success.main">
              Saved
            </Typography>
          </Box>
        )}
      </Box>

      <TextField
        value={notes}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={pdfHash ? "Take notes about this document…" : "Open a PDF to start taking notes."}
        disabled={!pdfHash}
        multiline
        fullWidth
        variant="standard"
        slotProps={{ input: { disableUnderline: true } }}
        sx={{
          flex: 1,
          "& .MuiInputBase-root": {
            height: "100%",
            alignItems: "flex-start",
            px: 2,
            py: 2,
            fontSize: 14,
            lineHeight: 1.6,
          },
          "& .MuiInputBase-input": {
            height: "100% !important",
            overflow: "auto !important",
          },
        }}
      />
    </Box>
  );
}
