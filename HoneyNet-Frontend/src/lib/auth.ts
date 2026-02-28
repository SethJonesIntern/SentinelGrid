
const LS_KEY = "sg_auth_user";

export type AuthedUser = { username: string };

export function getUser(): AuthedUser | null {
  const raw = localStorage.getItem(LS_KEY);
  return raw ? (JSON.parse(raw) as AuthedUser) : null;
}

export function login(username: string) {
  const user = { username: username || "student" };
  localStorage.setItem(LS_KEY, JSON.stringify(user));
  return user;
}

export function logout() {
  localStorage.removeItem(LS_KEY);
}