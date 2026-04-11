// localStorage helpers — mirrors desktop .chat_history.json and .notes.json
// All data keyed by PDF MD5 hash

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface PDFState {
  conversation: Message[];
  notes: string;
  lastPage: number;
}

function key(hash: string, field: keyof PDFState) {
  return `rh:${hash}:${field}`;
}

export function loadConversation(hash: string): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(key(hash, "conversation"));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveConversation(hash: string, messages: Message[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(key(hash, "conversation"), JSON.stringify(messages));
}

export function loadNotes(hash: string): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(key(hash, "notes")) ?? "";
}

export function saveNotes(hash: string, notes: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(key(hash, "notes"), notes);
}

export function loadLastPage(hash: string): number {
  if (typeof window === "undefined") return 0;
  return parseInt(localStorage.getItem(key(hash, "lastPage")) ?? "0", 10);
}

export function saveLastPage(hash: string, page: number) {
  if (typeof window === "undefined") return;
  localStorage.setItem(key(hash, "lastPage"), String(page));
}

export function loadPreference<T>(field: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(`rh:pref:${field}`);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function savePreference<T>(field: string, value: T) {
  if (typeof window === "undefined") return;
  localStorage.setItem(`rh:pref:${field}`, JSON.stringify(value));
}

// API key — stored in localStorage, never sent to our servers except as a
// transient Authorization header on each Gemini proxied request.
export function loadApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("rh:apiKey") ?? "";
}

export function saveApiKey(key: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("rh:apiKey", key);
}

export function clearApiKey() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("rh:apiKey");
}
