"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { saveLastPage } from "@/lib/storage";

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

  const [selecting, setSelecting] = useState(false);
  const [selStart, setSelStart] = useState<{ x: number; y: number } | null>(null);
  const [selRect, setSelRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  // Load PDF.js lazily (it's large and browser-only)
  const loadPdf = useCallback(async () => {
    if (!fileBytes) return;
    const pdfjsLib = await import("pdfjs-dist");
    pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;
    const pdf = await pdfjsLib.getDocument({ data: fileBytes }).promise;
    pdfRef.current = pdf;
    onTotalPages(pdf.numPages);
  }, [fileBytes, onTotalPages]);

  useEffect(() => {
    loadPdf();
  }, [loadPdf]);

  // Render page whenever currentPage or zoom changes
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
  }, [currentPage, zoom, pdfRef.current]);

  // --- Selection handling ---
  function getCanvasPos(e: React.MouseEvent) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  function onMouseDown(e: React.MouseEvent) {
    if (!pdfRef.current) return;
    setSelecting(true);
    const pos = getCanvasPos(e);
    setSelStart(pos);
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

    // Extract text from selection
    const page = await pdfRef.current.getPage(currentPage + 1);
    const viewport = page.getViewport({ scale: zoom });

    // Convert canvas coords → PDF coords
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

    // Capture image of selection from canvas at 2x resolution
    let imageBase64: string | null = null;
    if (rect.w > 5 && rect.h > 5) {
      const offscreen = document.createElement("canvas");
      const scale = 2;
      offscreen.width = rect.w * scale;
      offscreen.height = rect.h * scale;
      const octx = offscreen.getContext("2d")!;
      octx.drawImage(
        canvasRef.current,
        rect.x, rect.y, rect.w, rect.h,
        0, 0, rect.w * scale, rect.h * scale
      );
      imageBase64 = offscreen.toDataURL("image/png").split(",")[1];
    }

    if (selectedText || imageBase64) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      onSelection({
        text: selectedText,
        imageBase64,
        x: canvasRect.left + rect.x + rect.w / 2,
        y: canvasRect.top + rect.y,
      });
    }

    setSelRect(null);
  }

  function goTo(page: number) {
    const clamped = Math.max(0, Math.min(page, totalPages - 1));
    onPageChange(clamped);
    if (pdfHash) saveLastPage(pdfHash, clamped);
  }

  return (
    <div className="flex flex-col h-full" style={{ background: "#1a1a1a" }}>
      {/* Canvas area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex justify-center"
        style={{ background: "#333" }}
      >
        <div className="relative select-none" style={{ userSelect: "none" }}>
          <canvas
            ref={canvasRef}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            style={{ display: "block", cursor: "crosshair" }}
          />
          {/* Selection overlay */}
          {selRect && (
            <div
              style={{
                position: "absolute",
                left: selRect.x,
                top: selRect.y,
                width: selRect.w,
                height: selRect.h,
                background: "rgba(74, 158, 255, 0.25)",
                border: "1px solid rgba(74, 158, 255, 0.6)",
                pointerEvents: "none",
              }}
            />
          )}
        </div>
      </div>

      {/* Navigation */}
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ background: "#2d2d2d", borderTop: "1px solid #444" }}
      >
        <button
          onClick={() => goTo(currentPage - 1)}
          disabled={currentPage === 0}
          className="px-4 py-2 rounded text-sm disabled:opacity-40"
          style={{ background: "#3d3d3d", color: "#e0e0e0" }}
        >
          ◀ Previous
        </button>
        <span style={{ color: "#e0e0e0", fontSize: 14 }}>
          {totalPages > 0 ? `Page ${currentPage + 1} / ${totalPages}` : "—"}
        </span>
        <button
          onClick={() => goTo(currentPage + 1)}
          disabled={currentPage >= totalPages - 1}
          className="px-4 py-2 rounded text-sm disabled:opacity-40"
          style={{ background: "#3d3d3d", color: "#e0e0e0" }}
        >
          Next ▶
        </button>
      </div>
    </div>
  );
}
