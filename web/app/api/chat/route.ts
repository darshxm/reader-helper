// POST /api/chat — streaming chat with Gemini, using uploaded file reference
//
// The user's Gemini API key is read from the Authorization header (Bearer token).
// It is never stored — used only for this request.

import { NextRequest } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { SYSTEM_INSTRUCTION } from "@/lib/gemini";
import type { Message } from "@/lib/storage";

export const runtime = "nodejs";
export const maxDuration = 60;

function getApiKey(req: NextRequest): string | null {
  const auth = req.headers.get("authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7).trim();
  return null;
}

export async function POST(req: NextRequest) {
  const apiKey = getApiKey(req);
  if (!apiKey) {
    return new Response(JSON.stringify({ error: "API key required" }), { status: 401 });
  }

  const body = await req.json() as {
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

  const client = new GoogleGenAI({ apiKey });

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
    },
  });
}
