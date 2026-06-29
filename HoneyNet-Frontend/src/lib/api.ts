
export type HoneypotEventJson = {
  timestamp: string;
  src_ip: string;
  event_type: string;
  sensor_id?: string | null;
  session_id: string;
  payload: Record<string, unknown>;
  // populated by backend geolocation enrichment
  lat?: number | null;
  lon?: number | null;
  country?: string | null;
  city?: string | null;
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

export type AuthUser = {
  id: number | string;
  email: string;
};

export type TokenResponse = {
  access_token: string;
  token_type?: string;
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
    const text = await res.text().catch(() => "");
    // FastAPI's HTTPException bodies look like {"detail": "..."} — surface that
    // directly. Pydantic validation errors (422) instead return detail as an
    // array of {msg, loc, ...} objects, so handle both shapes.
    let detail = "";
    try {
      const parsed = JSON.parse(text)?.detail;
      if (typeof parsed === "string") detail = parsed;
      else if (Array.isArray(parsed)) {
        detail = parsed.map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d))).join("; ");
      }
    } catch { /* not JSON */ }
    throw new Error(detail || text || `HTTP ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

function authHeader(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export const api = {

  logs: (limit = 200) =>
    http<SessionsResponse>(`/logs?limit=${encodeURIComponent(limit)}`),

  auth: {
    signup: (email: string, password: string) =>
      http<TokenResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password })
      }),

    login: (email: string, password: string) =>
      http<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      }),

    me: (token: string) =>
      http<AuthUser>("/auth/me", { headers: authHeader(token) })
  }
};