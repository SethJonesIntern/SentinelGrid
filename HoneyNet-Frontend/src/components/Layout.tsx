import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getUser, logout } from "../lib/auth";
import Globe from "./Globe";

function NavItem({ to, label }: { to: string; label: string }) {
  const loc = useLocation();
  const active = loc.pathname === to || loc.pathname.startsWith(to + "/");

  return (
    <Link
      to={to}
      style={{
        border: active ? "1px solid rgba(99,165,255,0.5)" : "1px solid rgba(255,255,255,0.1)",
        background: active
          ? "linear-gradient(135deg, rgba(59,130,246,0.25), rgba(37,99,235,0.15))"
          : "rgba(255,255,255,0.03)",
        color: active ? "#93c5fd" : "#8896b0",
        padding: "7px 16px",
        borderRadius: "8px",
        textDecoration: "none",
        fontWeight: active ? 700 : 500,
        fontSize: 13,
        letterSpacing: "0.04em",
        boxShadow: active ? "0 0 16px rgba(59,130,246,0.2)" : "none",
        transition: "background 100ms ease, border-color 100ms ease, color 100ms ease, box-shadow 100ms ease"
      }}
    >
      {label}
    </Link>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const user = getUser();
  const navigate = useNavigate();

  return (
    <>
      {/* Stars using box-shadow technique */}
      <div className="stars1" />
      <div className="stars2" />
      <div className="stars3" />

      {/* Globe */}
      <Globe />

      <div
        style={{
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column"
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 28px",
            position: "sticky",
            top: 0,
            zIndex: 100
          }}
        >
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: 7,
              background: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              boxShadow: "0 0 16px rgba(59,130,246,0.4)"
            }}>
              ⬡
            </div>
            <span style={{
              fontWeight: 900,
              fontSize: 16,
              letterSpacing: "0.08em",
              color: "#e2e8f4",
              textTransform: "uppercase"
            }}>
              SentinelGrid
            </span>
          </div>

          {/* Nav */}
          <nav style={{ display: "flex", gap: 6 }}>
            <NavItem to="/dashboard" label="Dashboard" />
            <NavItem to="/live" label="Live Feed" />
            <NavItem to="/sessions" label="Sessions" />
            <NavItem to="/analytics" label="Analytics" />
            <NavItem to="/distribution" label="Distribution" />
          </nav>

          {/* User */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 12px",
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.03)"
            }}>
              <div style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "linear-gradient(135deg, #3b82f6, #22d3ee)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 11,
                fontWeight: 900,
                color: "#020510"
              }}>
                {(user?.email?.[0] ?? "S").toUpperCase()}
              </div>
              <span style={{ fontSize: 13, color: "#a8b5cc", fontWeight: 600 }}>
                {user?.email ?? "student"}
              </span>
            </div>

            <button
              onClick={() => { logout(); navigate("/login"); }}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "1px solid rgba(248,113,113,0.25)",
                background: "rgba(248,113,113,0.08)",
                color: "#f87171",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: "0.04em",
                fontFamily: "inherit",
                transition: "all 0.2s"
              }}
            >
              Log out
            </button>
          </div>
        </header>

        <main style={{ flex: 1, padding: "24px 28px", maxWidth: 1600, width: "100%", margin: "0 auto" }}>
          {children}
        </main>

        {/* Bottom status bar */}
        <footer style={{
          padding: "8px 28px",
          borderTop: "1px solid rgba(255,255,255,0.04)",
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontSize: 11,
          color: "#3d4f6e",
          fontFamily: "'Space Mono', monospace"
        }}>
          <span style={{ color: "#22d3ee" }}>●</span>
          <span>SYSTEM ONLINE</span>
          <span>|</span>
          <span>SENTINELGRID v2.0</span>
        </footer>
      </div>
    </>
  );
}