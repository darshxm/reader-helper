"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import CloseIcon from "@mui/icons-material/Close";

export const TOUR_KEY = "rh:tourCompleted";

const TOOLTIP_W = 320;
const SPOT_PAD = 8;   // spotlight padding around target
const GAP = 14;        // gap between spotlight edge and tooltip

type Placement = "top" | "bottom" | "left" | "right";

interface Step {
  target?: string;       // matches data-tour="…" on a DOM element
  title: string;
  body: React.ReactNode;
  placement?: Placement;
  beforeShow?: () => void;
}

function makeSteps(activateChat: () => void): Step[] {
  return [
    {
      title: "Welcome to PDF Reader Helper 👋",
      body: (
        <Box>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            AI-powered PDF reading with Google Gemini. Let's take a 30-second tour of the
            key features.
          </Typography>
          <Link
            href="https://github.com/darshxm/reader-helper"
            target="_blank"
            rel="noopener noreferrer"
            variant="body2"
          >
            View source on GitHub →
          </Link>
        </Box>
      ),
    },
    {
      target: "open-pdf",
      placement: "bottom",
      title: "Upload a Paper",
      body: (
        <Typography variant="body2">
          Click to open any PDF up to <strong>4 MB</strong>. Your file goes directly to Gemini —
          nothing is stored on our servers.
        </Typography>
      ),
    },
    {
      target: "pdf-viewer",
      placement: "right",
      title: "Select to Explain",
      body: (
        <Typography variant="body2">
          <strong>Click and drag</strong> anywhere on the document to select text or an image
          region. A button appears above the selection — click it to send it straight to Gemini.
        </Typography>
      ),
    },
    {
      target: "chat-input",
      placement: "top",
      beforeShow: activateChat,
      title: "Ask Anything",
      body: (
        <Typography variant="body2">
          Type any question about the document and press <strong>Enter</strong> or click Send.
          Gemini has access to the full PDF, not just what's visible on screen.
        </Typography>
      ),
    },
    {
      target: "quick-actions",
      placement: "top",
      beforeShow: activateChat,
      title: "Quick Follow-ups",
      body: (
        <Typography variant="body2">
          After a response, use these buttons to instantly ask for a simpler explanation, a
          concrete real-world example, or why the concept matters.
        </Typography>
      ),
    },
    {
      title: "You're all set! 🎉",
      body: (
        <Box>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            You get <strong>10 free messages</strong> to try the app. After that, add your own
            Gemini API key — it's free and you only pay for what you use.
          </Typography>
          <Typography variant="body2">
            Questions or feedback?{" "}
            <Link
              href="https://github.com/darshxm/reader-helper"
              target="_blank"
              rel="noopener noreferrer"
            >
              Open an issue on GitHub
            </Link>
            .
          </Typography>
        </Box>
      ),
    },
  ];
}

// ── Positioning helpers ──────────────────────────────────────────────────────

function getTargetRect(target?: string): DOMRect | null {
  if (!target) return null;
  return document.querySelector(`[data-tour="${target}"]`)?.getBoundingClientRect() ?? null;
}

function calcTooltipStyle(rect: DOMRect | null, placement?: Placement): React.CSSProperties {
  if (!rect) {
    // No target — centred modal
    return {
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: TOOLTIP_W,
      zIndex: 10001,
    };
  }

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const clampX = (x: number) => Math.max(8, Math.min(x, vw - TOOLTIP_W - 8));
  const midX = clampX(rect.left + rect.width / 2 - TOOLTIP_W / 2);

  switch (placement) {
    case "bottom":
      return { position: "fixed", top: rect.bottom + GAP, left: midX, width: TOOLTIP_W, zIndex: 10001 };
    case "top":
      return { position: "fixed", bottom: vh - rect.top + GAP, left: midX, width: TOOLTIP_W, zIndex: 10001 };
    case "left":
      return { position: "fixed", top: Math.max(8, rect.top), left: clampX(rect.left - TOOLTIP_W - GAP), width: TOOLTIP_W, zIndex: 10001 };
    case "right":
      return { position: "fixed", top: Math.max(8, rect.top), left: Math.min(rect.right + GAP, vw - TOOLTIP_W - 8), width: TOOLTIP_W, zIndex: 10001 };
    default:
      return { position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: TOOLTIP_W, zIndex: 10001 };
  }
}

// ── Component ────────────────────────────────────────────────────────────────

interface Props {
  onActivateChat: () => void;
  onFinish: () => void;
}

export default function AppTour({ onActivateChat, onFinish }: Props) {
  const steps = makeSteps(onActivateChat);
  const [stepIdx, setStepIdx] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const step = steps[stepIdx];
  const isLast = stepIdx === steps.length - 1;

  // Measure target element (after beforeShow side-effects settle)
  useEffect(() => {
    step.beforeShow?.();
    const t = setTimeout(() => setRect(getTargetRect(step.target)), 60);
    return () => clearTimeout(t);
  }, [stepIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-measure on resize
  useEffect(() => {
    const handler = () => setRect(getTargetRect(step.target));
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [step.target]);

  function finish() {
    localStorage.setItem(TOUR_KEY, "true");
    onFinish();
  }

  function next() {
    isLast ? finish() : setStepIdx((i) => i + 1);
  }

  const spotX = rect ? rect.x - SPOT_PAD : 0;
  const spotY = rect ? rect.y - SPOT_PAD : 0;
  const spotW = rect ? rect.width + SPOT_PAD * 2 : 0;
  const spotH = rect ? rect.height + SPOT_PAD * 2 : 0;

  return (
    <>
      {/* ── Overlay with spotlight cutout ────────────────────────────── */}
      <svg
        style={{
          position: "fixed",
          inset: 0,
          width: "100%",
          height: "100%",
          zIndex: 10000,
          // Allow clicks on the tooltip card (handled by stopPropagation there)
          pointerEvents: "all",
        }}
      >
        <defs>
          <mask id="tour-spotlight">
            <rect width="100%" height="100%" fill="white" />
            {rect && (
              <rect x={spotX} y={spotY} width={spotW} height={spotH} rx={6} fill="black" />
            )}
          </mask>
        </defs>

        {/* Dark backdrop */}
        <rect width="100%" height="100%" fill="rgba(0,0,0,0.65)" mask="url(#tour-spotlight)" />

        {/* Animated spotlight border */}
        {rect && (
          <rect
            x={spotX}
            y={spotY}
            width={spotW}
            height={spotH}
            rx={6}
            fill="none"
            stroke="rgba(74,158,255,0.8)"
            strokeWidth={2}
            strokeDasharray="6 3"
          >
            <animate attributeName="stroke-dashoffset" from="0" to="-18" dur="1s" repeatCount="indefinite" />
          </rect>
        )}
      </svg>

      {/* ── Tooltip card ─────────────────────────────────────────────── */}
      <Box
        style={calcTooltipStyle(rect, step.placement)}
        onClick={(e) => e.stopPropagation()}
      >
        <Paper elevation={8} sx={{ borderRadius: 2, overflow: "hidden" }}>
          {/* Blue accent bar */}
          <Box sx={{ height: 3, bgcolor: "primary.main" }} />

          <Box sx={{ p: 2.5 }}>
            {/* Progress dots */}
            <Box sx={{ display: "flex", gap: 0.75, mb: 2, alignItems: "center" }}>
              {steps.map((_, i) => (
                <Box
                  key={i}
                  sx={{
                    height: 5,
                    width: i === stepIdx ? 20 : 5,
                    borderRadius: 3,
                    bgcolor: i === stepIdx ? "primary.main" : i < stepIdx ? "primary.dark" : "action.disabled",
                    transition: "width 0.25s ease, background-color 0.25s ease",
                  }}
                />
              ))}
              <Typography variant="caption" color="text.disabled" sx={{ ml: "auto" }}>
                {stepIdx + 1} / {steps.length}
              </Typography>
            </Box>

            {/* Title + close */}
            <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1.4 }}>
                {step.title}
              </Typography>
              <IconButton
                size="small"
                onClick={finish}
                sx={{ mt: -0.5, mr: -0.75, color: "text.disabled", flexShrink: 0 }}
              >
                <CloseIcon sx={{ fontSize: 15 }} />
              </IconButton>
            </Box>

            {/* Body */}
            <Box sx={{ mb: 2.5, color: "text.secondary" }}>{step.body}</Box>

            {/* Actions */}
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Button
                size="small"
                onClick={finish}
                sx={{ color: "text.disabled", fontSize: 12, minWidth: 0, px: 1 }}
              >
                Skip
              </Button>
              <Button size="small" variant="contained" onClick={next} disableElevation sx={{ px: 2 }}>
                {isLast ? "Done" : "Next →"}
              </Button>
            </Box>
          </Box>
        </Paper>
      </Box>
    </>
  );
}
