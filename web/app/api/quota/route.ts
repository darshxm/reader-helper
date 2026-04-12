// GET /api/quota — returns free tier availability and remaining message count for this IP.
// Used by the frontend on load to decide whether to show the API key gate.

import { NextRequest, NextResponse } from "next/server";
import { freeTierConfigured, getClientIP, peekFreeQuota, FREE_LIMIT } from "@/lib/redis";

export async function GET(req: NextRequest) {
  const available = freeTierConfigured();

  if (!available) {
    return NextResponse.json({ available: false, remaining: 0, limit: FREE_LIMIT });
  }

  const ip = getClientIP(req);
  const quota = await peekFreeQuota(ip);

  return NextResponse.json({
    available: true,
    remaining: quota?.remaining ?? FREE_LIMIT,
    limit: FREE_LIMIT,
  });
}
