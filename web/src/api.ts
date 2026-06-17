import type { GameState } from "./types";

const normalizeApiBase = (value: string) => value.trim().replace(/\/+$/, "");

export const apiBase = () => {
  const params = new URLSearchParams(window.location.search);
  return normalizeApiBase(params.get("api") || import.meta.env.VITE_API_BASE || "");
};

export const apiUrl = (path: string) => {
  if (/^https?:\/\//i.test(path)) return path;
  const base = apiBase();
  if (!base) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
};

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail?.detail?.message || detail?.message || response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function loadState() {
  return api<GameState>("/api/game/state");
}

export type StreamEvent =
  | { type: "stage"; message: string }
  | { type: "narrative"; message: string }
  | { type: "done"; payload: any }
  | { type: "error"; message: string };

export async function issueDecreeStream(onEvent: (event: StreamEvent) => void) {
  const response = await fetch(apiUrl("/api/decree/issue/stream"), { method: "POST" });
  if (!response.ok || !response.body) throw new Error("颁诏失败。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const lines = chunk.split(/\r?\n/);
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) continue;
      const type = eventLine.slice(6).trim() as StreamEvent["type"];
      const data = JSON.parse(dataLine.slice(5).trim());
      onEvent({ type, ...data } as StreamEvent);
    }
    if (done) break;
  }
}

