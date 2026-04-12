// POST /api/upload — receives PDF bytes, uploads to Gemini Files API
// GET  /api/upload?hash=... — always returns cache miss (no KV available)
//
// Auth: user's own key via Authorization header, or server GEMINI_API_KEY as fallback.
// Uploads are not quota-counted — only chat messages are.

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";

function getApiKey(req: NextRequest): string | null {
  const auth = req.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  const key = auth.slice(7).trim();
  return key || null;
}

// No KV available — always a cache miss; client will upload fresh
export async function GET(_req: NextRequest) {
  return NextResponse.json({ fileName: null, cached: false });
}

export async function POST(req: NextRequest) {
  const apiKeyToUse = getApiKey(req) ?? process.env.GEMINI_API_KEY ?? null;

  if (!apiKeyToUse) {
    return NextResponse.json({ error: "API key required" }, { status: 401 });
  }

  const formData = await req.formData();
  const file = formData.get("file") as File | null;
  const hash = formData.get("hash") as string | null;

  if (!file || !hash) {
    return NextResponse.json({ error: "file and hash required" }, { status: 400 });
  }

  const MAX_BYTES = 4 * 1024 * 1024;
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { error: `File too large (max 4 MB, got ${(file.size / 1024 / 1024).toFixed(1)} MB)` },
      { status: 413 },
    );
  }

  try {
    const client = new GoogleGenAI({ apiKey: apiKeyToUse });
    const bytes = await file.arrayBuffer();
    const blob = new Blob([bytes], { type: "application/pdf" });

    const uploaded = await client.files.upload({
      file: blob,
      config: { mimeType: "application/pdf" },
    });

    return NextResponse.json({ fileName: uploaded.name!, cached: false });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upload failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export const maxDuration = 60;
