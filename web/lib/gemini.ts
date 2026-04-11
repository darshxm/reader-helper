import { GoogleGenAI } from "@google/genai";

export const AVAILABLE_MODELS = [
  "gemini-flash-latest",
  "gemini-pro-latest",
  "gemini-2.0-flash",
];

export const DEFAULT_MODEL = "gemini-flash-latest";

export const CACHE_EXPIRY_HOURS = 47;

export const SYSTEM_INSTRUCTION = `You are a helpful reading assistant. Your job is to help users understand complex documents, papers, and books.

Key behaviors:
- Explain concepts in simple, accessible language
- Define technical terms when they appear
- Use analogies and real-world examples
- Be concise but thorough
- If asked to simplify, really dumb it down - assume zero background knowledge
- Reference specific parts of the document when relevant
- You have access to the full document - use it to provide context-aware answers`;

let _client: GoogleGenAI | null = null;

export function getGeminiClient(): GoogleGenAI {
  if (!_client) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) throw new Error("GEMINI_API_KEY not set");
    _client = new GoogleGenAI({ apiKey });
  }
  return _client;
}
