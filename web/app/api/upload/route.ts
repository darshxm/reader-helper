// POST /api/upload — receives PDF bytes, uploads to Gemini Files API, caches in KV
// GET  /api/upload?hash=... — checks KV cache for existing upload
//
// The user's Gemini API key is read from the Authorization header (Bearer token).
// It is never stored — used only for this request.

import { NextRequest, NextResponse } from "next/server";
import { kv } from "@vercel/kv";
import { GoogleGenAI } from "@google/genai";
import { CACHE_EXPIRY_HOURS } from "@/lib/gemini";

interface CacheEntry {
  fileName: string;
  uploadTime: string;
}

const KV_PREFIX = "gemini-file:";
const TTL_SECONDS = CACHE_EXPIRY_HOURS * 60 * 60;

function getApiKey(req: NextRequest): string | null {
  const auth = req.headers.get("authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7).trim();
  return null;
}

export async function GET(req: NextRequest) {
  const hash = req.nextUrl.searchParams.get("hash");
  if (!hash) return NextResponse.json({ error: "hash required" }, { status: 400 });

  try {
    const entry = await kv.get<CacheEntry>(`${KV_PREFIX}${hash}`);
    if (entry) {
      return NextResponse.json({ fileName: entry.fileName, cached: true });
    }
    return NextResponse.json({ fileName: null, cached: false });
  } catch {
    return NextResponse.json({ fileName: null, cached: false });
  }
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

  // Check cache first
  try {
    const existing = await kv.get<CacheEntry>(`${KV_PREFIX}${hash}`);
    if (existing) {
      return NextResponse.json({ fileName: existing.fileName, cached: true });
    }
  } catch {
    // KV unavailable — continue with upload
  }

  try {
    const client = new GoogleGenAI({ apiKey });
    const bytes = await file.arrayBuffer();
    const blob = new Blob([bytes], { type: "application/pdf" });

    const uploaded = await client.files.upload({
      file: blob,
      config: { mimeType: "application/pdf" },
    });

    const fileName = uploaded.name!;

    try {
      await kv.set(
        `${KV_PREFIX}${hash}`,
        { fileName, uploadTime: new Date().toISOString() } satisfies CacheEntry,
        { ex: TTL_SECONDS }
      );
    } catch {
      // KV unavailable — skip caching
    }

    return NextResponse.json({ fileName, cached: false });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upload failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export const maxDuration = 60;
