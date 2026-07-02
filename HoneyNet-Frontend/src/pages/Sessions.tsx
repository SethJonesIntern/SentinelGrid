import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import { formatTimestamp, groupBySession } from "../lib/telemetry";
import Dropdown from "../components/Dropdown";

const KNOWN_EVENT_TYPES = [
  "cowrie.command.input",
  "cowrie.direct-tcpip.request",
  "cowrie.login.success",
  "cowrie.session.closed",
  "cowrie.session.connect",
  "ftp.login.success",
  "ftp.session.connect",
  "ftp.session.disconnect",
  "http.page.visit",
  "http.scan.probe",
  "mysql.session.connect",
  "mysql.session.end",
  "redis.session.connect",
  "redis.session.disconnect",
  "smtp.ehlo",
  "smtp.login.attempt",
  "smtp.session.connect",
  "smtp.session.disconnect",
  "ssh.login.attempt",
];

export default function SessionsPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(200);
  const [page, setPage] = useState(0);
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
  useEffect(() => { setPage(0); }, [ipFilter, typeFilter, sidFilter, limit]);

  const PAGE_SIZE = 50;

  const sessions = useMemo(() => {
    return groupBySession(logs).filter((s) => {
      const okIp = ipFilter ? s.src_ip.includes(ipFilter.trim()) : true;
      const okSid = sidFilter ? s.session_id.includes(sidFilter.trim()) : true;
      const okType = typeFilter ? s.event_types.some((t) => t.includes(typeFilter.trim())) : true;
      return okIp && okSid && okType;
    });
  }, [logs, ipFilter, sidFilter, typeFilter]);

  const totalPages = Math.ceil(sessions.length / PAGE_SIZE);
  const pageSessions = sessions.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Session Explorer</div>
            <div style={subtle}>Investigate grouped activity by session_id.</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: loading ? "#fbbf24" : err ? "#f87171" : "#34d399", display: "inline-block" }} />
            <span style={subtle}>{loading ? "Loading..." : err ? "Error" : `${sessions.length} sessions`}</span>
          </div>
        </div>

        <div style={filtersRow}>
          <input value={ipFilter} onChange={(e) => setIpFilter(e.target.value)} placeholder="Filter src_ip" style={inputStyle} />
          <Dropdown
            value={typeFilter}
            onChange={setTypeFilter}
            placeholder="All event types"
            options={[
              { label: "All event types", value: "" },
              ...Array.from(new Set([...KNOWN_EVENT_TYPES, ...logs.map((l) => l.raw_json.event_type).filter(Boolean)])).sort().map((t) => ({ label: t, value: t }))
            ]}
          />
          <input value={sidFilter} onChange={(e) => setSidFilter(e.target.value)} placeholder="Filter session_id" style={inputStyle} />
          <label style={fieldLabel} title="Number of most-recent events to fetch (50–1000)">
            Limit
            <input
              type="number" min={50} max={1000} value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={{ ...inputStyle, width: 90 }}
            />
          </label>
          <button onClick={() => void load()} style={btn}>Refresh</button>
        </div>

        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 10 }}>{err}</div>}
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <MiniStat label="Total Sessions" value={String(sessions.length)} accent="#3b82f6" />
        <MiniStat label="Events Loaded" value={String(logs.length)} accent="#22d3ee" />
        <MiniStat label="Unique IPs" value={String(new Set(logs.map(l => l.raw_json.src_ip).filter(Boolean)).size)} accent="#f87171" />
        <MiniStat label="Fetch Limit" value={String(limit)} accent="#fbbf24" />
      </div>

      {/* Table */}
      <div style={panel}>
        <div style={{ ...sectionLabel, marginBottom: 16 }}>
          Sessions — <span style={{ color: "#3b82f6" }}>{sessions.length}</span> grouped
        </div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Session ID</th>
                <th>src_ip</th>
                <th>Events</th>
                <th>Event Types</th>
                <th>Commands</th>
                <th>First Seen</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {pageSessions.map((s) => (
                <tr key={s.session_id}>
                  <td>
                    <Link
                      to={`/sessions/${encodeURIComponent(s.session_id)}`}
                      style={{ color: "#60a5fa", textDecoration: "none" }}
                    >
                      <span style={pill}>{s.session_id.slice(0, 12)}…</span>
                    </Link>
                    <div style={{ fontSize: 10, color: "#3d4f6e", marginTop: 5, wordBreak: "break-all", fontFamily: "'Space Mono', monospace" }}>
                      {s.session_id}
                    </div>
                  </td>
                  <td><span style={pill}>{s.src_ip}</span></td>
                  <td>
                    <span style={{ fontSize: 18, fontWeight: 900, color: "#93c5fd" }}>{s.count}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                      {s.event_types.slice(0, 4).map((t) => (
                        <span key={t} style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.25)" }}>{t}</span>
                      ))}
                      {s.event_types.length > 4 && (
                        <span style={{ ...pill, color: "#4b5f7c" }}>+{s.event_types.length - 4}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    {s.commands.length === 0 ? (
                      <span style={{ color: "#2a3a52", fontSize: 12 }}>—</span>
                    ) : (
                      <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                        {s.commands.slice(0, 3).map((cmd) => (
                          <span key={cmd} style={{ ...pill, color: "#34d399", borderColor: "rgba(52,211,153,0.25)" }}>{cmd}</span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{formatTimestamp(s.oldest_ts)}</div>
                  </td>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{formatTimestamp(s.newest_ts)}</div>
                  </td>
                </tr>
              ))}
              {!loading && sessions.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <div style={{ ...subtle, padding: "16px 0", display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ color: "#2a3a52" }}>◉</span>
                      {typeFilter
                        ? `No "${typeFilter}" sessions found in ${logs.length} fetched logs.`
                        : "No sessions match your filters."}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 16 }}>
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} style={{ ...btn, opacity: page === 0 ? 0.4 : 1 }}>← Prev</button>
            <span style={subtle}>Page {page + 1} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} style={{ ...btn, opacity: page >= totalPages - 1 ? 0.4 : 1 }}>Next →</button>
          </div>
        )}
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
const filtersRow: React.CSSProperties = { display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16, alignItems: "flex-end" };

const fieldLabel: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: 5,
  fontSize: 10,
  color: "#6b7a99",
  fontFamily: "'Space Mono', monospace",
  whiteSpace: "nowrap",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
};

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