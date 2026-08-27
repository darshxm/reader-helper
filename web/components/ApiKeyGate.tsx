"use client";

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

interface Props {
  onSave: (key: string) => void;
  quotaExhausted?: boolean;
}

export default function ApiKeyGate({ onSave, quotaExhausted = false }: Props) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Please enter your API key.");
      return;
    }
    onSave(trimmed);
  }

  return (
    <Dialog open fullWidth maxWidth="sm" slotProps={{ paper: { sx: { bgcolor: "background.paper" } } }}>
      <DialogTitle sx={{ pb: 0 }}>
        {quotaExhausted ? "Free messages used up" : "Enter your Gemini API key"}
      </DialogTitle>
      <DialogContent>
        {quotaExhausted ? (
          <Alert severity="info" sx={{ mt: 1, mb: 2 }}>
            You've used your 10 free messages. Add your own Gemini API key to keep going — it's
            free to get and you only pay for what you use.
          </Alert>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 1 }}>
            This app uses your own Google Gemini API key. It is stored only in your browser and
            sent directly to Gemini over HTTPS — never stored on any server.
          </Typography>
        )}

        <Link
          href="https://aistudio.google.com/app/apikey"
          target="_blank"
          rel="noopener noreferrer"
          variant="body2"
          sx={{ display: "block", mb: 3 }}
        >
          Get a free API key from Google AI Studio →
        </Link>

        <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            type="password"
            value={value}
            onChange={(e) => { setValue(e.target.value); setError(""); }}
            placeholder="AIzaSy..."
            autoFocus
            fullWidth
            size="small"
            label="API Key"
            autoComplete="new-password"
          />
          {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
          <Button type="submit" variant="contained" disabled={!value.trim()} fullWidth>
            Save &amp; continue
          </Button>
        </Box>

        <Typography variant="caption" color="text.disabled" sx={{ display: "block", mt: 2 }}>
          Your key is saved in localStorage and cleared if you click "Remove key" in the toolbar.
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
