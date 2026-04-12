// POST /api/log-error — receives client-side error reports and writes them to
// server-side console so they appear in Vercel runtime logs.
// No auth required; payload is sanitised before logging.

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const context = String(body?.context ?? "unknown").slice(0, 200);
    const message = String(body?.message ?? "").slice(0, 1000);
    const ua = String(body?.ua ?? "").slice(0, 500);
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";

    console.error(`[client-error] context=${context} ip=${ip} ua=${ua} message=${message}`);
  } catch {
    // Malformed body — nothing to log
  }

  return NextResponse.json({ ok: true });
}
