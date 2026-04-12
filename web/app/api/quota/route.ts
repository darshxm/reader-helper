// GET /api/quota — returns free tier availability and remaining message count.
// Also sets the rh-uid cookie on first visit (used as second factor alongside IP).

import { NextRequest, NextResponse } from "next/server";
import {
  freeTierConfigured,
  getClientIP,
  peekFreeQuota,
  FREE_LIMIT,
  UID_COOKIE,
  uidCookieHeader,
} from "@/lib/redis";

export async function GET(req: NextRequest) {
  const available = freeTierConfigured();

  if (!available) {
    return NextResponse.json({ available: false, remaining: 0, limit: FREE_LIMIT });
  }

  const ip = getClientIP(req);
  const existingUid = req.cookies.get(UID_COOKIE)?.value ?? null;
  const quota = await peekFreeQuota(ip, existingUid);

  const response = NextResponse.json({
    available: true,
    remaining: quota?.remaining ?? FREE_LIMIT,
    limit: FREE_LIMIT,
  });

  // Set a fresh UID cookie if the visitor doesn't have one yet
  if (!existingUid) {
    const newUid = crypto.randomUUID();
    response.headers.set("Set-Cookie", uidCookieHeader(newUid));
  }

  return response;
}
