import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getUser, logout } from "../lib/auth";

function NavItem({ to, label }: { to: string; label: string }) {
  const loc = useLocation();
  const active = loc.pathname === to;

  return (
    <Link
      to={to}
      className="pill"
      style={{
        borderColor: active ? "rgba(96,165,250,0.55)" : undefined,
        background: active ? "rgba(96,165,250,0.12)" : undefined,
        color: active ? "rgba(226,232,240,0.98)" : undefined
      }}
    >
      {label}
    </Link>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const user = getUser();
  const nav = useNavigate();

  return (
    <div>
      {/* Top bar */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          borderBottom: "1px solid rgba(148,163,184,0.16)",
          background: "rgba(7,10,18,0.60)",
          backdropFilter: "blur(10px)"
        }}
      >
        <div className="container" style={{ padding: "18px 0" }}>
          <div
            style={{
              display: "flex",
              gap: 14,
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap"
            }}
          >
            <div style={{ minWidth: 240 }}>
              <div className="h1">SentinelGrid</div>
              <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>
                Student dashboard • honeypot telemetry
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <NavItem to="/dashboard" label="Dashboard" />
              <NavItem to="/sessions" label="Sessions" />
              <span className="muted" style={{ fontSize: 12 }}>
                {user?.username}
              </span>

              <button
                className="btn secondary"
                onClick={() => {
                  logout();
                  nav("/login");
                }}
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Page content */}
      <div className="container" style={{ padding: "22px 0 44px" }}>
        {children}
      </div>
    </div>
  );
}