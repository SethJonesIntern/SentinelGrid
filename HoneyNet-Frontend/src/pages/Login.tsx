import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUser, login } from "../lib/auth";

export default function LoginPage() {
  const nav = useNavigate();
  const [username, setUsername] = useState("student");
  const [password, setPassword] = useState("password");

  useEffect(() => {
    if (getUser()) nav("/dashboard");
  }, [nav]);

  return (
    <div
      style={{
        minHeight: "calc(100vh - 40px)",
        display: "grid",
        placeItems: "center",
        padding: 20
      }}
    >
      <div className="card padded" style={{ width: "min(520px, 100%)" }}>
        <div className="h1">Sign in</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Mock login for now. Backend auth can come later.
        </div>

        <div style={{ marginTop: 18, display: "grid", gap: 12 }}>
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
              Username
            </div>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
              Password
            </div>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            className="btn"
            onClick={() => {
              login(username.trim());
              nav("/dashboard");
            }}
          >
            Log in
          </button>
        </div>
      </div>
    </div>
  );
}