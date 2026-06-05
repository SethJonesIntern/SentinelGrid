
export type HoneypotEventJson = {
  timestamp: string;
  src_ip: string;
  event_type: string;
  sensor_id?: string | null;
  session_id: string;
  payload: Record<string, unknown>;
};

export type RawLogRow = {
  id: number;
  created_at: string;
  raw_json: HoneypotEventJson;
};

export type SessionsResponse = {
  count: number;
  logs: RawLogRow[];
};

function readRuntimeApiUrl(): string | null {
  const anyWin = window as unknown as { __ENV__?: { API_URL?: string } };
  return anyWin.__ENV__?.API_URL ?? null;
}

export const API_URL =
  readRuntimeApiUrl() ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} ${msg}`);
  }
  return (await res.json()) as T;
}

export const api = {
  
  logs: (limit = 200) =>
    http<SessionsResponse>(`/logs?limit=${encodeURIComponent(limit)}`)
};