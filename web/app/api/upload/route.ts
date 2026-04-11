// POST /api/upload — receives PDF bytes, uploads to Gemini Files API
// GET  /api/upload?hash=... — always returns cache miss (no KV available)
//
// The user's Gemini API key is read from the Authorization header (Bearer token).
// It is never stored — used only for this request.

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";

function getApiKey(req: NextRequest): string | null {
  const auth = req.headers.get("authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7).trim();
  return null;
}

// No KV available — always a cache miss; client will upload fresh
export async function GET(_req: NextRequest) {
  return NextResponse.json({ fileName: null, cached: false });
}

export async function POST(req: NextRequest) {
  const apiKey = getApiKey(req);
  if (!apiKey) {
    return NextResponse.json({ error: "API key required" }, { status: 401 });
  }

  const formData = await req.formData();
  const file = formData.get("file") as File | null;
  const hash = formData.get("hash") as string | null;

  if (!file || !hash) {
    return NextResponse.json({ error: "file and hash required" }, { status: 400 });
  }

  try {
    const client = new GoogleGenAI({ apiKey });
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
