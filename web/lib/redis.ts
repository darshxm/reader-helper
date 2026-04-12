import { Redis } from "@upstash/redis";
import { NextRequest } from "next/server";

export const FREE_LIMIT = 10;
// Cookie name stored in browser; httpOnly so JS can't read/tamper it
export const UID_COOKIE = "rh-uid";

let _client: Redis | null = null;

export function getRedisClient(): Redis | null {
  if (_client) return _client;
  const url = process.env.UPSTASH_REDIS_REST_URL?.trim().replace(/\/$/, "");
  const token = process.env.UPSTASH_REDIS_REST_TOKEN?.trim();
  if (!url || !token) return null;
  try {
    _client = new Redis({ url, token });
  } catch (e) {
    console.error("[redis] Failed to initialise Upstash client:", e);
    return null;
  }
  return _client;
}

export function freeTierConfigured(): boolean {
  return !!(process.env.GEMINI_API_KEY && getRedisClient());
}

export function getClientIP(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "anonymous"
  );
}

/** Cookie attributes for Set-Cookie header */
export function uidCookieHeader(uid: string): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${UID_COOKIE}=${uid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000${secure}`;
}

/**
 * Increment both the IP counter and the UID (cookie) counter.
 * A request is allowed only when BOTH are within the limit.
 * `remaining` is the lower of the two — the binding constraint.
 */
export async function consumeFreeMessage(
  ip: string,
  uid: string,
): Promise<{ allowed: boolean; remaining: number } | null> {
  const redis = getRedisClient();
  if (!redis) return null;

  const [ipCount, uidCount] = await Promise.all([
    redis.incr(`rh:free:ip:${ip}`),
    redis.incr(`rh:free:uid:${uid}`),
  ]);

  const ipRemaining = Math.max(0, FREE_LIMIT - ipCount);
  const uidRemaining = Math.max(0, FREE_LIMIT - uidCount);
  return {
    allowed: ipCount <= FREE_LIMIT && uidCount <= FREE_LIMIT,
    remaining: Math.min(ipRemaining, uidRemaining),
  };
}

/**
 * Read current quota without consuming. Returns null if Redis not configured.
 * If uid is null (no cookie yet) the UID bucket is treated as empty (full quota).
 */
export async function peekFreeQuota(
  ip: string,
  uid: string | null,
): Promise<{ remaining: number; limit: number } | null> {
  const redis = getRedisClient();
  if (!redis) return null;

  const [ipCount, uidCount] = await Promise.all([
    redis.get<number>(`rh:free:ip:${ip}`).then((v) => v ?? 0),
    uid
      ? redis.get<number>(`rh:free:uid:${uid}`).then((v) => v ?? 0)
      : Promise.resolve(0),
  ]);

  const ipRemaining = Math.max(0, FREE_LIMIT - ipCount);
  const uidRemaining = Math.max(0, FREE_LIMIT - uidCount);
  return { remaining: Math.min(ipRemaining, uidRemaining), limit: FREE_LIMIT };
}
