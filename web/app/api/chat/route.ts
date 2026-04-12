// POST /api/chat — streaming chat with Gemini, using uploaded file reference.
//
// Auth priority:
//   1. Authorization: Bearer <user-key>  →  use user's own key (unlimited)
//   2. No header                         →  use server GEMINI_API_KEY with per-IP free quota
//   3. No header + quota exhausted       →  429 QUOTA_EXHAUSTED

import { NextRequest } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { SYSTEM_INSTRUCTION, AVAILABLE_MODELS } from "@/lib/gemini";
import {
  consumeFreeMessage,
  freeTierConfigured,
  getClientIP,
  UID_COOKIE,
  uidCookieHeader,
} from "@/lib/redis";
import type { Message } from "@/lib/storage";

export const runtime = "nodejs";
export const maxDuration = 60;

function getApiKey(req: NextRequest): string | null {
  const auth = req.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  const key = auth.slice(7).trim();
  return key || null;
}

export async function POST(req: NextRequest) {
  const userApiKey = getApiKey(req);

  let apiKeyToUse: string;
  let freeRemaining: number | null = null;
  let setCookieHeader: string | null = null;

  if (userApiKey) {
    apiKeyToUse = userApiKey;
  } else {
    // Free-tier path: use server key, enforced by per-IP + per-UID quota
    if (!freeTierConfigured()) {
      return new Response(JSON.stringify({ error: "API key required" }), { status: 401 });
    }

    const ip = getClientIP(req);
    const existingUid = req.cookies.get(UID_COOKIE)?.value;
    const uid = existingUid ?? crypto.randomUUID();
    if (!existingUid) setCookieHeader = uidCookieHeader(uid);

    const quota = await consumeFreeMessage(ip, uid);

    if (!quota || !quota.allowed) {
      return new Response(
        JSON.stringify({
          error: "Free quota exhausted. Please add your own Gemini API key to continue.",
          code: "QUOTA_EXHAUSTED",
        }),
        { status: 429 },
      );
    }

    apiKeyToUse = process.env.GEMINI_API_KEY!;
    freeRemaining = quota.remaining;
  }

  const body = (await req.json()) as {
    message: string;
    model: string;
    fileName: string;
    history: Message[];
    imageBase64?: string;
  };

  const { message, model, fileName, history, imageBase64 } = body;

  if (!message && !imageBase64) {
    return new Response(JSON.stringify({ error: "message required" }), { status: 400 });
  }

  if (!model || !AVAILABLE_MODELS.includes(model)) {
    return new Response(JSON.stringify({ error: "invalid model" }), { status: 400 });
  }

  if (fileName && !/^files\/[a-zA-Z0-9_-]+$/.test(fileName)) {
    return new Response(JSON.stringify({ error: "invalid fileName" }), { status: 400 });
  }

  const client = new GoogleGenAI({ apiKey: apiKeyToUse });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const parts: any[] = [];

  if (fileName) {
    parts.push({
      fileData: {
        fileUri: `https://generativelanguage.googleapis.com/v1beta/${fileName}`,
        mimeType: "application/pdf",
      },
    });
  }

  if (history.length > 0) {
    const historyText = history
      .map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
      .join("\n\n");
    parts.push({ text: `Previous conversation:\n${historyText}\n\n---\n\n` });
  }

  if (imageBase64) {
    parts.push({ inlineData: { mimeType: "image/png", data: imageBase64 } });
  }

  parts.push({ text: message || "Please explain what is shown in this image." });

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const result = await client.models.generateContentStream({
          model,
          contents: [{ role: "user", parts }],
          config: { systemInstruction: SYSTEM_INSTRUCTION },
        });

        for await (const chunk of result) {
          const text = chunk.text ?? "";
          if (text) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`));
          }
        }

        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Gemini error";
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: msg })}\n\n`));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      ...(freeRemaining !== null && { "X-Free-Remaining": String(freeRemaining) }),
      ...(setCookieHeader && { "Set-Cookie": setCookieHeader }),
    },
  });
}
