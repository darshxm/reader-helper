import { Redis } from "@upstash/redis";
import { NextRequest } from "next/server";

export const FREE_LIMIT = 10;

let _client: Redis | null = null;

export function getRedisClient(): Redis | null {
  if (_client) return _client;
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return null;
  }
  _client = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  });
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

/** Increment and return quota state. Returns null if Redis is not configured. */
export async function consumeFreeMessage(
  ip: string,
): Promise<{ allowed: boolean; remaining: number } | null> {
  const redis = getRedisClient();
  if (!redis) return null;

  const key = `rh:free:${ip}`;
  const count = await redis.incr(key);
  const remaining = Math.max(0, FREE_LIMIT - count);
  return { allowed: count <= FREE_LIMIT, remaining };
}

/** Read current quota without consuming it. Returns null if Redis is not configured. */
export async function peekFreeQuota(
  ip: string,
): Promise<{ remaining: number; limit: number } | null> {
  const redis = getRedisClient();
  if (!redis) return null;

  const count = (await redis.get<number>(`rh:free:${ip}`)) ?? 0;
  return { remaining: Math.max(0, FREE_LIMIT - count), limit: FREE_LIMIT };
}
