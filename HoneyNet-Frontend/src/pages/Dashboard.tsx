import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import {
  buildTopEventTypes,
  buildTopIps,
  formatTimestamp,
  getCommandText,
  groupBySession,
  timeAgo
} from "../lib/telemetry";

export default function DashboardPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [pollMs, setPollMs] = useState(5000);
  const [autoRefresh, setAutoRefresh] = useState(true);

  async function load() {
    try {
      setErr("");
      const res = await api.logs(200);
      setLogs(res.logs);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => void load(), pollMs);
    return () => window.clearInterval(id);
  }, [autoRefresh, pollMs]);

  const sessions = useMemo(() => groupBySession(logs), [logs]);
  const topIps = useMemo(() => buildTopIps(logs, 5), [logs]);
  const topEvents = useMemo(() => buildTopEventTypes(logs, 5), [logs]);
  const latest = logs.slice(0, 10);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {/* Header panel */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Attack Dashboard</div>
            <div style={subtle}>Real-time telemetry from <code style={{ color: "#60a5fa", fontSize: 11 }}>GET /logs</code></div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <label style={{ ...subtle, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto-refresh
            </label>
            <select value={pollMs} onChange={(e) => setPollMs(Number(e.target.value))} style={selectStyle}>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
              <option value={30000}>30s</option>
              <option value={60000}>60s</option>
            </select>
            <button onClick={() => void load()} style={btn}>Refresh now</button>
          </div>
        </div>
        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 10 }}>{err}</div>}
      </div>

      {/* Stats */}
      <div style={statsGrid}>
        <StatCard label="Events Loaded" value={String(logs.length)} accent="#3b82f6" />
        <StatCard label="Unique Sessions" value={String(sessions.length)} accent="#22d3ee" />
        <StatCard label="Source IPs" value={String(new Set(logs.map(l => l.raw_json.src_ip)).size)} accent="#f87171" />
        <StatCard label="Polling" value={autoRefresh ? `${pollMs / 1000}s` : "Paused"} accent="#34d399" />
      </div>

      {/* Top IPs + Event Types */}
      <div style={twoCol}>
        <div style={panel}>
          <div style={sectionLabel}>Top Source IPs</div>
          {topIps.length === 0 ? <EmptyState /> : (
            <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
              {topIps.map((item, i) => (
                <div key={item.label} style={barRow}>
                  <span style={monoTag}>{item.label}</span>
                  <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{
                      height: 4,
                      borderRadius: 2,
                      width: `${(item.value / topIps[0].value) * 100}%`,
                      background: `linear-gradient(90deg, #3b82f6, #1d4ed8)`,
                      opacity: 1 - i * 0.12,
                      minWidth: 4
                    }} />
                    <strong style={{ fontSize: 13, color: "#93c5fd" }}>{item.value}</strong>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={panel}>
          <div style={sectionLabel}>Top Event Types</div>
          {topEvents.length === 0 ? <EmptyState /> : (
            <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
              {topEvents.map((item, i) => {
                const eventColors = ["#3b82f6","#22d3ee","#34d399","#f59e0b","#f472b6"];
                return (
                  <div key={item.label} style={barRow}>
                    <span style={monoTag}>{item.label}</span>
                    <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{
                        height: 4,
                        borderRadius: 2,
                        width: `${(item.value / topEvents[0].value) * 100}%`,
                        background: eventColors[i % 5],
                        minWidth: 4,
                        opacity: 0.8
                      }} />
                      <strong style={{ fontSize: 13, color: eventColors[i % 5] }}>{item.value}</strong>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Live feed table */}
      <div style={panel}>
        <div style={{ ...topRow, marginBottom: 16 }}>
          <div style={sectionLabel}>Live Feed</div>
          <span style={{
            ...subtle,
            display: "flex",
            alignItems: "center",
            gap: 6
          }}>
            <span style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: loading ? "#fbbf24" : err ? "#f87171" : autoRefresh ? "#34d399" : "#6b7a99",
              display: "inline-block"
            }} />
            {loading ? "Loading..." : err ? "Error" : autoRefresh ? "Live" : "Paused"}
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp</th>
                <th>src_ip</th>
                <th>Event Type</th>
                <th>Session ID</th>
                <th>Command</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((l) => (
                <tr key={l.id}>
                  <td style={{ color: "#4b5f7c", fontSize: 12 }}>{l.id}</td>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{formatTimestamp(l.raw_json.timestamp)}</div>
                    <div style={{ fontSize: 11, color: "#4b5f7c", marginTop: 2 }}>{timeAgo(l.raw_json.timestamp)}</div>
                  </td>
                  <td><span style={pill}>{l.raw_json.src_ip}</span></td>
                  <td><span style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.3)" }}>{l.raw_json.event_type}</span></td>
                  <td>
                    <Link to={`/sessions/${encodeURIComponent(l.raw_json.session_id)}`} style={{ color: "#60a5fa", fontSize: 12, fontFamily: "'Space Mono', monospace" }}>
                      {l.raw_json.session_id.slice(0, 14)}…
                    </Link>
                  </td>
                  <td style={{ fontSize: 12, color: "#a8b5cc" }}>{getCommandText(l)}</td>
                </tr>
              ))}
              {!loading && latest.length === 0 && (
                <tr>
                  <td colSpan={6}><EmptyState /></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ ...panel, borderColor: `${accent}22`, position: "relative", overflow: "hidden" }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, ${accent}, transparent)`
      }} />
      <div style={subtle}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6, color: accent, lineHeight: 1 }}>{value}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{ ...subtle, padding: "16px 0", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ color: "#2a3a52" }}>◉</span>
      No telemetry yet — events will appear automatically.
    </div>
  );
}

const panel: React.CSSProperties = {
  background: "rgba(6,10,24,0.7)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid rgba(255,255,255,0.08)",
  boxShadow: "0 0 40px rgba(59,130,246,0.08), inset 0 1px 0 rgba(255,255,255,0.04)",
  borderRadius: 14,
  padding: "20px 24px"
};

const pageTitle: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 900,
  letterSpacing: "0.02em",
  color: "#e2e8f4"
};

const sectionLabel: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: "#4b5f7c"
};

const subtle: React.CSSProperties = {
  color: "#6b7a99",
  fontSize: 12
};

const topRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  flexWrap: "wrap"
};

const statsGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: 12
};

const twoCol: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 12
};

const barRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12
};

const selectStyle: React.CSSProperties = {
  padding: "7px 12px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(255,255,255,0.03)",
  color: "#a8b5cc",
  fontSize: 12,
  cursor: "pointer"
};

const btn: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: 9,
  border: "1px solid rgba(99,165,255,0.3)",
  background: "rgba(59,130,246,0.12)",
  color: "#93c5fd",
  cursor: "pointer",
  fontWeight: 700,
  fontSize: 13,
  fontFamily: "inherit"
};

const pill: React.CSSProperties = {
  display: "inline-block",
  padding: "3px 10px",
  borderRadius: 999,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(255,255,255,0.04)",
  color: "#c8d3e8",
  fontSize: 11,
  fontFamily: "'Space Mono', monospace"
};

const monoTag: React.CSSProperties = {
  fontSize: 11,
  fontFamily: "'Space Mono', monospace",
  color: "#8896b0",
  minWidth: 120,
  flexShrink: 0
};