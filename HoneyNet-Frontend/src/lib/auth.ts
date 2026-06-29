import { api } from "./api";
import type { AuthUser } from "./api";

export type { AuthUser };

const TOKEN_KEY = "sg_auth_token";
const USER_KEY = "sg_auth_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

function setSession(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// Dev-only escape hatch so the app is usable while the real backend auth is
// unreachable/unfinished. `import.meta.env.DEV` is a compile-time constant —
// Vite strips this branch out of production builds entirely, so it can never
// ship in a deployed build.
const DEV_BYPASS_USERNAME = "devuser";
const DEV_BYPASS_PASSWORD = "devbypass";

export async function login(username: string, password: string): Promise<AuthUser> {
  if (import.meta.env.DEV && username === DEV_BYPASS_USERNAME && password === DEV_BYPASS_PASSWORD) {
    console.warn("[auth] Using DEV-only bypass login — not a real backend session.");
    const user: AuthUser = { id: "dev", username: DEV_BYPASS_USERNAME };
    setSession("dev-bypass-token", user);
    return user;
  }

  const { access_token } = await api.auth.login(username, password);
  const user = await api.auth.me(access_token);
  setSession(access_token, user);
  return user;
}

export async function signup(username: string, password: string, email?: string): Promise<AuthUser> {
  const { access_token } = await api.auth.signup(username, password, email);
  const user = await api.auth.me(access_token);
  setSession(access_token, user);
  return user;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
