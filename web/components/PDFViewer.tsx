"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { saveLastPage } from "@/lib/storage";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";

interface SelectionInfo {
  text: string;
  imageBase64: string | null;
  x: number;
  y: number;
}

interface Props {
  fileBytes: Uint8Array | null;
  pdfHash: string | null;
  onSelection: (info: SelectionInfo) => void;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages: number;
  onTotalPages: (n: number) => void;
  zoom: number;
}

export default function PDFViewer({
  fileBytes,
  pdfHash,
  onSelection,
  currentPage,
  onPageChange,
  totalPages,
  onTotalPages,
  zoom,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pdfRef = useRef<any>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  const [pdfVersion, setPdfVersion] = useState(0);
  const [selecting, setSelecting] = useState(false);
  const [selStart, setSelStart] = useState<{ x: number; y: number } | null>(null);
  const [selRect, setSelRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  const loadPdf = useCallback(async () => {
    if (!fileBytes) return;
    const pdfjsLib = await import("pdfjs-dist");
    const workerBlob = new Blob(
      [`import '${location.origin}/pdf.worker.min.mjs'`],
      { type: "application/javascript" }
    );
    pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(workerBlob);
    const pdf = await pdfjsLib.getDocument({ data: fileBytes.slice() }).promise;
    pdfRef.current = pdf;
    onTotalPages(pdf.numPages);
    setPdfVersion((v) => v + 1);
  }, [fileBytes, onTotalPages]);

  useEffect(() => {
    loadPdf();
  }, [loadPdf]);

  useEffect(() => {
    async function render() {
      if (!pdfRef.current || !canvasRef.current) return;

      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }

      const page = await pdfRef.current.getPage(currentPage + 1);
      const viewport = page.getViewport({ scale: zoom });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d")!;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const task = page.render({ canvasContext: ctx, viewport });
      renderTaskRef.current = task;
      try {
        await task.promise;
      } catch {
        // Cancelled — ignore
      }
    }
    render();
  }, [currentPage, zoom, pdfVersion]);

  function getCanvasPos(e: React.MouseEvent) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function onMouseDown(e: React.MouseEvent) {
    if (!pdfRef.current) return;
    setSelecting(true);
    setSelStart(getCanvasPos(e));
    setSelRect(null);
  }

  function onMouseMove(e: React.MouseEvent) {
    if (!selecting || !selStart) return;
    const pos = getCanvasPos(e);
    setSelRect({
      x: Math.min(selStart.x, pos.x),
      y: Math.min(selStart.y, pos.y),
      w: Math.abs(pos.x - selStart.x),
      h: Math.abs(pos.y - selStart.y),
    });
  }

  async function onMouseUp(e: React.MouseEvent) {
    if (!selecting) return;
    setSelecting(false);

    const pos = getCanvasPos(e);
    if (!selStart || !canvasRef.current || !pdfRef.current) return;

    const rect = {
      x: Math.min(selStart.x, pos.x),
      y: Math.min(selStart.y, pos.y),
      w: Math.abs(pos.x - selStart.x),
      h: Math.abs(pos.y - selStart.y),
    };

    if (rect.w < 5 && rect.h < 5) {
      setSelRect(null);
      return;
    }

    const page = await pdfRef.current.getPage(currentPage + 1);
    const viewport = page.getViewport({ scale: zoom });

    const pdfX1 = rect.x / zoom;
    const pdfY1 = rect.y / zoom;
    const pdfX2 = (rect.x + rect.w) / zoom;
    const pdfY2 = (rect.y + rect.h) / zoom;

    const pageHeight = viewport.height / zoom;
    const pdfRect = [pdfX1, pageHeight - pdfY2, pdfX2, pageHeight - pdfY1];

    const textContent = await page.getTextContent();
    const selectedText = textContent.items
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .filter((item: any) => {
        const [, , , , tx, ty] = item.transform;
        return tx >= pdfRect[0] && tx <= pdfRect[2] && ty >= pdfRect[1] && ty <= pdfRect[3];
      })
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .map((item: any) => item.str)
      .join(" ");

    let imageBase64: string | null = null;
    if (rect.w > 5 && rect.h > 5) {
      const offscreen = document.createElement("canvas");
      const scale = 2;
      offscreen.width = rect.w * scale;
      offscreen.height = rect.h * scale;
      const octx = offscreen.getContext("2d")!;
      octx.drawImage(canvasRef.current, rect.x, rect.y, rect.w, rect.h, 0, 0, rect.w * scale, rect.h * scale);
      imageBase64 = offscreen.toDataURL("image/png").split(",")[1];
    }

    if (selectedText || imageBase64) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      onSelection({ text: selectedText, imageBase64, x: canvasRect.left + rect.x + rect.w / 2, y: canvasRect.top + rect.y });
    }

    setSelRect(null);
  }

  function goTo(page: number) {
    const clamped = Math.max(0, Math.min(page, totalPages - 1));
    onPageChange(clamped);
    if (pdfHash) saveLastPage(pdfHash, clamped);
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", bgcolor: "#1a1a1a" }}>
      {/* Canvas area */}
      <Box
        ref={containerRef}
        sx={{ flex: 1, overflowAuto: "auto", overflow: "auto", display: "flex", justifyContent: "center", bgcolor: "#333" }}
      >
        <Box sx={{ position: "relative", userSelect: "none" }}>
          <canvas
            ref={canvasRef}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            style={{ display: "block", cursor: "crosshair" }}
          />
          {selRect && (
            <Box
              sx={{
                position: "absolute",
                left: selRect.x,
                top: selRect.y,
                width: selRect.w,
                height: selRect.h,
                bgcolor: "rgba(74, 158, 255, 0.2)",
                border: "1px solid rgba(74, 158, 255, 0.6)",
                pointerEvents: "none",
              }}
            />
          )}
        </Box>
      </Box>

      {/* Navigation */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 0.75,
          bgcolor: "background.paper",
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        <IconButton
          onClick={() => goTo(currentPage - 1)}
          disabled={currentPage === 0}
          size="small"
          color="inherit"
        >
          <ChevronLeftIcon />
        </IconButton>
        <Typography variant="body2" color="text.secondary">
          {totalPages > 0 ? `${currentPage + 1} / ${totalPages}` : "—"}
        </Typography>
        <IconButton
          onClick={() => goTo(currentPage + 1)}
          disabled={currentPage >= totalPages - 1}
          size="small"
          color="inherit"
        >
          <ChevronRightIcon />
        </IconButton>
      </Box>
    </Box>
  );
}
