import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import { formatTimestamp, getCommandText, timeAgo } from "../lib/telemetry";

export default function LiveFeedPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(200);
  const [pollMs, setPollMs] = useState(5000);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [ipFilter, setIpFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [sidFilter, setSidFilter] = useState("");

  async function load() {
    try {
      setErr("");
      const res = await api.logs(limit);
      setLogs(res.logs);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [limit]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => void load(), pollMs);
    return () => window.clearInterval(id);
  }, [autoRefresh, pollMs, limit]);

  const filtered = useMemo(() => logs.filter((l) => {
    const okIp = ipFilter ? l.raw_json.src_ip.includes(ipFilter.trim()) : true;
    const okType = typeFilter ? l.raw_json.event_type.includes(typeFilter.trim()) : true;
    const okSid = sidFilter ? l.raw_json.session_id.includes(sidFilter.trim()) : true;
    return okIp && okType && okSid;
  }), [logs, ipFilter, typeFilter, sidFilter]);

  const statusColor = loading ? "#fbbf24" : err ? "#f87171" : autoRefresh ? "#34d399" : "#6b7a99";
  const statusText = loading ? "Loading..." : err ? "Error" : autoRefresh ? "Live" : "Paused";

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Live Attack Feed</div>
            <div style={subtle}>Streaming latest events from the telemetry backend.</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: statusColor, display: "inline-block", boxShadow: `0 0 8px ${statusColor}` }} />
            <span style={subtle}>{statusText}</span>
          </div>
        </div>

        {/* Filters */}
        <div style={filtersRow}>
          <input value={ipFilter} onChange={(e) => setIpFilter(e.target.value)} placeholder="Filter src_ip" style={inputStyle} />
          <input value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} placeholder="Filter event_type" style={inputStyle} />
          <input value={sidFilter} onChange={(e) => setSidFilter(e.target.value)} placeholder="Filter session_id" style={inputStyle} />
          <input
            type="number" min={50} max={1000} value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ ...inputStyle, width: 90 }}
          />
          <select value={pollMs} onChange={(e) => setPollMs(Number(e.target.value))} style={inputStyle}>
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
            <option value={60000}>60s</option>
          </select>
          <button onClick={() => setAutoRefresh((v) => !v)} style={autoRefresh ? btnDanger : btn}>
            {autoRefresh ? "Pause" : "Resume"}
          </button>
          <button onClick={() => void load()} style={btn}>Refresh</button>
        </div>

        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 10 }}>{err}</div>}
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <MiniStat label="Total Fetched" value={String(logs.length)} accent="#3b82f6" />
        <MiniStat label="Filtered Events" value={String(filtered.length)} accent="#22d3ee" />
        <MiniStat label="Unique IPs" value={String(new Set(logs.map(l => l.raw_json.src_ip)).size)} accent="#f87171" />
        <MiniStat label="Poll Interval" value={autoRefresh ? `${pollMs / 1000}s` : "Paused"} accent="#34d399" />
      </div>

      {/* Table */}
      <div style={panel}>
        <div style={{ ...sectionLabel, marginBottom: 16 }}>
          Event Stream — <span style={{ color: "#3b82f6" }}>{filtered.length}</span> events
        </div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>src_ip</th>
                <th>Event Type</th>
                <th>Session ID</th>
                <th>Command</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l) => (
                <tr key={l.id}>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{formatTimestamp(l.raw_json.timestamp)}</div>
                    <div style={{ fontSize: 11, color: "#4b5f7c", marginTop: 2 }}>{timeAgo(l.raw_json.timestamp)}</div>
                  </td>
                  <td><span style={pill}>{l.raw_json.src_ip}</span></td>
                  <td><span style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.3)" }}>{l.raw_json.event_type}</span></td>
                  <td style={{ maxWidth: 200, wordBreak: "break-all" }}>
                    <span style={{ fontSize: 11, fontFamily: "'Space Mono', monospace", color: "#6b7a99" }}>
                      {l.raw_json.session_id}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: "#a8b5cc" }}>{getCommandText(l)}</td>
                  <td style={{ maxWidth: 300 }}>
                    <pre style={preStyle}>{JSON.stringify(l.raw_json.payload ?? {}, null, 2)}</pre>
                  </td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <div style={{ ...subtle, padding: "16px 0", display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ color: "#2a3a52" }}>◉</span>
                      No matching events found.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ ...panel, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${accent}, transparent)` }} />
      <div style={subtle}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 900, marginTop: 6, color: accent, lineHeight: 1 }}>{value}</div>
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
  padding: "20px 24px",
};

const pageTitle: React.CSSProperties = { fontSize: 22, fontWeight: 900, letterSpacing: "0.02em", color: "#e2e8f4" };
const sectionLabel: React.CSSProperties = { fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#4b5f7c" };
const subtle: React.CSSProperties = { color: "#6b7a99", fontSize: 12 };

const topRow: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" };
const filtersRow: React.CSSProperties = { display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16, alignItems: "center" };

const inputStyle: React.CSSProperties = {
  minWidth: 160,
  padding: "8px 12px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(255,255,255,0.03)",
  color: "#e2e8f4",
  fontSize: 12,
  fontFamily: "'Space Mono', monospace",
  outline: "none",
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
  fontFamily: "inherit",
};

const btnDanger: React.CSSProperties = {
  ...btn,
  border: "1px solid rgba(248,113,113,0.3)",
  background: "rgba(248,113,113,0.1)",
  color: "#f87171",
};

const pill: React.CSSProperties = {
  display: "inline-block",
  padding: "3px 10px",
  borderRadius: 999,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(255,255,255,0.04)",
  color: "#c8d3e8",
  fontSize: 11,
  fontFamily: "'Space Mono', monospace",
};

const preStyle: React.CSSProperties = {
  margin: 0,
  whiteSpace: "pre-wrap",
  color: "#6b7a99",
  fontSize: 11,
  fontFamily: "'Space Mono', monospace",
};