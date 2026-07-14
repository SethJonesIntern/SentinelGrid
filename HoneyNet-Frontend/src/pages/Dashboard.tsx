import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import {
  buildTopEventTypes,
  buildTopIps,
  formatTimestamp,
  groupBySession,
  timeAgo
} from "../lib/telemetry";
import Dropdown from "../components/Dropdown";

const POLL_MS_KEY = "sg_dashboard_poll_ms";

const KNOWN_EVENT_TYPES= [
  "cowrie.command.input","cowrie.direct-tcpip.request","cowrie.login.success",
  "cowrie.session.closed","cowrie.session.connect","ftp.login.success",
  "ftp.session.connect","ftp.session.disconnect","http.page.visit","http.scan.probe",
  "mysql.session.connect","mysql.session.end","redis.session.connect",
  "redis.session.disconnect","smtp.ehlo","smtp.login.attempt","smtp.session.connect",
  "smtp.session.disconnect","ssh.login.attempt",
];

export default function DashboardPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(200);
  const [pollMs, setPollMs] = useState<number>(() => {
    const stored = localStorage.getItem(POLL_MS_KEY);
    return stored ? Number(stored) : 15000;
  });
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [ipFilter, setIpFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [sidFilter, setSidFilter] = useState("");
  const [page, setPage] = useState(0);
  const loadGen = useRef(0);

  useEffect(() => { localStorage.setItem(POLL_MS_KEY, String(pollMs)); }, [pollMs]);

  async function load(resetPage = false) {
    const gen = ++loadGen.current;
    try {
      setErr("");
      const res = await api.logs(limit);
      if (gen !== loadGen.current) return;
      setLogs(res.logs);
      if (resetPage) setPage(0);
    } catch (e) {
      if (gen !== loadGen.current) return;
      setErr((e as Error).message);
    } finally {
      if (gen === loadGen.current) setLoading(false);
    }
  }

  useEffect(() => { void load(true); }, [limit]);
  useEffect(() => { setPage(0); }, [ipFilter, typeFilter, sidFilter, limit]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, pollMs);
    return () => window.clearInterval(id);
  }, [autoRefresh, pollMs, limit]);

  const PAGE_SIZE = 50;

  const filtered = useMemo(() => logs
    .filter((l) => {
      const okIp = ipFilter ? l.raw_json.src_ip?.includes(ipFilter.trim()) : true;
      const okType = typeFilter ? l.raw_json.event_type?.includes(typeFilter.trim()) : true;
      const okSid = sidFilter ? l.raw_json.session_id?.includes(sidFilter.trim()) : true;
      return okIp && okType && okSid;
    })
    .sort((a, b) => {
      const ts = (row: typeof a) => { const t = new Date(row.created_at ?? "").getTime(); return isNaN(t) ? row.id : t; };
      return ts(b) - ts(a);
    }),
  [logs, ipFilter, typeFilter, sidFilter]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const pageFiltered = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const sessions = useMemo(() => groupBySession(logs), [logs]);
  const topIps = useMemo(() => buildTopIps(logs, 5), [logs]);
  const topEvents = useMemo(() => buildTopEventTypes(logs, 5), [logs]);
  const statusColor = loading ? "#fbbf24" : err ? "#f87171" : autoRefresh ? "#34d399" : "#6b7a99";
  const statusText = loading ? "Loading..." : err ? "Error" : autoRefresh ? "Live" : "Paused";

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {/* header panel */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Attack Dashboard</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <label style={{ ...subtle, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
              Auto-refresh
            </label>
            <select value={pollMs} onChange={(e) => setPollMs(Number(e.target.value))} style={selectStyle}>
              <option value={5000} style={optionStyle}>5s</option>
              <option value={10000} style={optionStyle}>10s</option>
              <option value={15000} style={optionStyle}>15s</option>
              <option value={30000} style={optionStyle}>30s</option>
              <option value={60000} style={optionStyle}>60s</option>
            </select>
            <button onClick={() => void load(true)} style={btn}>Refresh now</button>
          </div>
        </div>
        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 10 }}>{err}</div>}
      </div>

      {/* stats */}
      <div style={statsGrid}>
        <StatCard label="Events Loaded" value={String(logs.length)} accent="#3b82f6" />
        <StatCard label="Unique Sessions" value={String(sessions.length)} accent="#22d3ee" />
        <StatCard label="Source IPs" value={String(new Set(logs.map(l => l.raw_json.src_ip).filter(Boolean)).size)} accent="#f87171" />
        <StatCard label="Polling" value={autoRefresh ? `${pollMs / 1000}s` : "Paused"} accent="#34d399" />
      </div>
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
        <div style={{ ...topRow, marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={sectionLabel}>Live Feed</div>
            <span style={{ display: "flex", alignItems: "center", gap: 5, ...subtle }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: statusColor, display: "inline-block" }} />
              {statusText}
            </span>
          </div>
        </div>

        {/* filters */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 16 }}>
          <input value={sidFilter} onChange={(e) => setSidFilter(e.target.value)} placeholder="Filter session_id" style={inputStyle} />
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
          <label style={{ ...subtle, display: "flex", alignItems: "center", gap: 6 }}>
            Limit
            <input type="number" min={50} max={1000} value={limit} onChange={(e) => setLimit(Number(e.target.value))} style={{ ...inputStyle, width: 80 }} />
          </label>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Timestamp</th>
                <th>src_ip</th>
                <th>Event Type</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {pageFiltered.map((l) => (
                <tr key={l.id}>
                  <td>
                    <Link to={`/sessions/${encodeURIComponent(l.raw_json.session_id)}`} style={{ color: "#60a5fa", fontSize: 11, fontFamily: "'Space Mono', monospace" }}>
                      {l.raw_json.session_id?.slice(0, 16)}…
                    </Link>
                  </td>
                  <td>
                    <div style={{ fontSize: 12, color: "#c8d3e8" }}>{formatTimestamp(l.created_at)}</div>
                    <div style={{ fontSize: 11, color: "#4b5f7c", marginTop: 2 }}>{timeAgo(l.created_at)}</div>
                  </td>
                  <td><span style={pill}>{l.raw_json.src_ip}</span></td>
                  <td><span style={{ ...pill, color: "#93c5fd", borderColor: "rgba(99,165,255,0.3)" }}>{l.raw_json.event_type}</span></td>
                  <td style={{ maxWidth: 300 }}>
                    <pre style={preStyle}>{JSON.stringify(l.raw_json.payload ?? {}, null, 2)}</pre>
                  </td>
                </tr>
              ))}
              {!loading && pageFiltered.length === 0 && (
                <tr><td colSpan={5}><EmptyState /></td></tr>
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
  cursor: "pointer",
  colorScheme: "dark"
};

const optionStyle: React.CSSProperties = {
  background: "#0a1024",
  color: "#e2e8f4"
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
  colorScheme: "dark",
};

const preStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 10,
  fontFamily: "'Space Mono', monospace",
  color: "#6b7a99",
  whiteSpace: "pre-wrap",
  wordBreak: "break-all",
  maxHeight: 60,
  overflow: "hidden",
};
