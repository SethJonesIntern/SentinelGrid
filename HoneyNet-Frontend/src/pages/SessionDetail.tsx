import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import { timeAgo } from "../lib/telemetry";

export default function SessionDetailPage() {
  const { sessionId } = useParams();
  const decoded = sessionId ? decodeURIComponent(sessionId) : "";
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setErr("");
        const res = await api.logs(1500);
        setLogs(res.logs.filter((l) => l.raw_json.session_id === decoded));
      } catch (e) {
        setErr((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [decoded]);

  const srcIp = logs[0]?.raw_json?.src_ip ?? "unknown";
  const eventTypes = [...new Set(logs.map(l => l.raw_json.event_type))];

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <Link to="/sessions" style={{ color: "#4b5f7c", fontSize: 12, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                ← Sessions
              </Link>
            </div>
            <div style={pageTitle}>Session Detail</div>
            <div style={{ fontSize: 11, color: "#3d4f6e", marginTop: 6, wordBreak: "break-all", fontFamily: "'Space Mono', monospace" }}>
              {decoded}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
          <span style={pill}>src_ip: <strong style={{ color: "#93c5fd" }}>{srcIp}</strong></span>
          <span style={pill}>events: <strong style={{ color: "#34d399" }}>{logs.length}</strong></span>
          <span style={{ ...pill, color: loading ? "#fbbf24" : err ? "#f87171" : "#34d399", borderColor: loading ? "rgba(251,191,36,0.3)" : err ? "rgba(248,113,113,0.3)" : "rgba(52,211,153,0.3)" }}>
            {loading ? "● Loading" : err ? "● Error" : "● OK"}
          </span>
          {eventTypes.map(t => (
            <span key={t} style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.25)" }}>{t}</span>
          ))}
        </div>

        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 10 }}>{err}</div>}
      </div>

      {/* Stats */}
      {logs.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
          <MiniStat label="Total Events" value={String(logs.length)} accent="#3b82f6" />
          <MiniStat label="Source IP" value={srcIp} accent="#f87171" />
          <MiniStat label="Event Types" value={String(eventTypes.length)} accent="#22d3ee" />
          <MiniStat label="Time Span" value={timeAgo(logs[logs.length - 1]?.raw_json.timestamp)} accent="#fbbf24" />
        </div>
      )}

      {/* Event table */}
      <div style={panel}>
        <div style={{ ...sectionLabel, marginBottom: 16 }}>
          Event Log — <span style={{ color: "#3b82f6" }}>{logs.length}</span> events
        </div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>Sensor</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontSize: 11, color: "#4b5f7c", fontFamily: "'Space Mono', monospace" }}>{l.id}</td>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{l.raw_json.timestamp}</div>
                    <div style={{ fontSize: 11, color: "#4b5f7c", marginTop: 2 }}>{timeAgo(l.raw_json.timestamp)}</div>
                  </td>
                  <td>
                    <span style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.25)" }}>
                      {l.raw_json.event_type}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: "#6b7a99" }}>{l.raw_json.sensor_id ?? "—"}</td>
                  <td>
                    <pre style={preStyle}>{JSON.stringify(l.raw_json.payload ?? {}, null, 2)}</pre>
                  </td>
                </tr>
              ))}
              {!loading && !err && logs.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div style={{ ...subtle, padding: "16px 0", display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ color: "#2a3a52" }}>◉</span>
                      No events found for this session within the current fetch limit.
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
      <div style={{ fontSize: 16, fontWeight: 900, marginTop: 6, color: accent, lineHeight: 1.2, wordBreak: "break-all" }}>{value}</div>
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
const topRow: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 };

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
  maxWidth: 400,
};