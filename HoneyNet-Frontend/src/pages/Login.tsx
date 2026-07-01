import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getUser, login } from "../lib/auth";

export default function LoginPage() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (getUser()) nav("/dashboard");
  }, [nav]);

  async function handleLogin() {
    if (!username.trim() || !password) { setError("Username and password are required"); return; }
    setError("");
    setLoading(true);
    try {
      await login(username.trim(), password);
      nav("/dashboard");
    } catch (e) {
      setError((e as Error).message || "Invalid username or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "grid",
      placeItems: "center",
      padding: 20,
      position: "relative",
      zIndex: 1
    }}>
      {/* Center glow */}
      <div style={{
        position: "absolute",
        width: 500,
        height: 500,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(29,78,216,0.12) 0%, transparent 70%)",
        pointerEvents: "none"
      }} />

      <div style={{
        width: "min(420px, 100%)",
        background: "rgba(6,10,24,0.85)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        border: "1px solid rgba(59,130,246,0.2)",
        borderRadius: 18,
        padding: "36px 32px",
        boxShadow: "0 0 80px rgba(29,78,216,0.15), inset 0 1px 0 rgba(255,255,255,0.06)",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Top accent line */}
        <div style={{
          position: "absolute",
          top: 0, left: 0, right: 0,
          height: 2,
          background: "linear-gradient(90deg, transparent, #3b82f6, #22d3ee, transparent)"
        }} />

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: "linear-gradient(135deg, #1d4ed8, #0e7490)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 24,
            margin: "0 auto 14px",
            boxShadow: "0 0 24px rgba(59,130,246,0.3)"
          }}>⬡</div>
          <div style={{ fontWeight: 900, fontSize: 20, letterSpacing: "0.08em", color: "#e2e8f4" }}>
            SENTINELGRID
          </div>
          <div style={{ fontSize: 11, color: "#3d4f6e", marginTop: 4, letterSpacing: "0.06em" }}>
            SECURITY OPERATIONS CENTER
          </div>
        </div>

        <div style={{ display: "grid", gap: 14 }}>
          <div>
            <div style={label}>Username</div>
            <input
              style={inputStyle}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              spellCheck={false}
            />
          </div>

          <div>
            <div style={label}>Password</div>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div style={{
              padding: "9px 12px",
              borderRadius: 8,
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.25)",
              color: "#f87171",
              fontSize: 12,
              fontFamily: "'Space Mono', monospace"
            }}>
              {error}
            </div>
          )}

          <button
            onClick={handleLogin}
            disabled={loading}
            style={{
              marginTop: 6,
              padding: "12px",
              borderRadius: 10,
              border: "1px solid rgba(99,165,255,0.35)",
              background: loading
                ? "rgba(59,130,246,0.1)"
                : "linear-gradient(135deg, rgba(59,130,246,0.25), rgba(29,78,216,0.2))",
              color: loading ? "#4b5f7c" : "#93c5fd",
              cursor: loading ? "default" : "pointer",
              fontWeight: 800,
              fontSize: 14,
              letterSpacing: "0.08em",
              fontFamily: "inherit",
              transition: "all 0.2s"
            }}
          >
            {loading ? "AUTHENTICATING..." : "ACCESS SYSTEM"}
          </button>

          

          <div style={{ textAlign: "center", fontSize: 12, color: "#3d5278" }}>
            Don't have an account?{" "}
            <Link to="/signup" style={{ color: "#3b82f6", textDecoration: "none", fontWeight: 700 }}>
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

const label: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: "0.12em",
  textTransform: "uppercase" as const,
  color: "#3d5278",
  marginBottom: 6,
  fontFamily: "'Space Mono', monospace"
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "11px 14px",
  borderRadius: 10,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(255,255,255,0.03)",
  color: "#e2e8f4",
  fontSize: 13,
  fontFamily: "'Space Mono', monospace",
  outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.2s"
};