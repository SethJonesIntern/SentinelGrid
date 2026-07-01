
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
  username: string;
  email?: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type?: string;
};

export type RedistributionResponse = {
  counts: Record<string, number>;
};

export type GeoCoordsResponse = {
  ip: string;
  latitude: number;
  longitude: number;
  city: string | null;
  country: string | null;
};

export type HoneynetStateResponse = {
  counts: Record<string, number>;
  total: number;
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

  sessions: (limit = 200) =>
    http<SessionsResponse>(`/sessions?limit=${encodeURIComponent(limit)}`),

  auth: {
    // Backend's `users` table requires username (unique, not null); email is
    // optional there, so signup takes it but login only needs username+password.
    signup: (username: string, password: string, email?: string) =>
      http<TokenResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ username, password, email: email || undefined })
      }),

    login: (username: string, password: string) =>
      http<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password })
      }),

    me: (token: string) =>
      http<AuthUser>("/auth/me", { headers: authHeader(token) })
  },

  geo: {
    coords: (ip: string) =>
      http<GeoCoordsResponse>(`/get_coords?ip=${encodeURIComponent(ip)}`),
  },

  ml: {
    // TODO: not reachable from the browser yet — GET /honeynet/state on the
    // backend (HoneyNet-Backend/app/routes/ml.py) is gated behind a
    // machine-only agent token. Once there's a user-facing way to read it,
    // point this at the real path; it should keep returning the actual
    // per-type honeypot counts currently running, unchanged.
    state: () =>
      http<HoneynetStateResponse>("/honeynet/state"),

    // TODO: not live yet — the backend redistribute endpoint (talks to the ML
    // model, runs the allocation, returns the resulting counts) is still being
    // built. Point this at the real path once it lands; expected response
    // shape is RedistributionResponse. The frontend does no ML/allocation
    // logic of its own — it only renders whatever counts come back here.
    redistribute: () =>
      http<RedistributionResponse>("/redistribute", { method: "POST" })
  }
};