import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";

type SessionRow = {
  session_id: string;
  src_ip: string;
  count: number;
  newest_id: number;
  newest_ts: string;
  event_types: string[];
};

function groupBySession(logs: RawLogRow[]): SessionRow[] {
  const m = new Map<string, RawLogRow[]>();

  for (const l of logs) {
    const sid = l.raw_json?.session_id ?? "unknown";
    if (!m.has(sid)) m.set(sid, []);
    m.get(sid)!.push(l);
  }

  const rows: SessionRow[] = [];

  for (const [session_id, items] of m.entries()) {
    // Sort newest first (bigger id = newer, based on your backend ordering)
    items.sort((a, b) => b.id - a.id);

    const newest = items[0];
    const src_ip = newest?.raw_json?.src_ip ?? "unknown";
    const newest_ts = newest?.raw_json?.timestamp ?? "";
    const newest_id = newest?.id ?? 0;

    const event_types = Array.from(
      new Set(items.map((x) => x.raw_json?.event_type ?? "unknown"))
    ).slice(0, 6);

    rows.push({
      session_id,
      src_ip,
      count: items.length,
      newest_id,
      newest_ts,
      event_types
    });
  }

  // newest sessions first
  rows.sort((a, b) => b.newest_id - a.newest_id);
  return rows;
}

export default function SessionsPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const [limit, setLimit] = useState(400);
  const [ipFilter, setIpFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [sidFilter, setSidFilter] = useState("");

  async function load() {
    try {
      setErr("");
      const res = await api.sessions(limit);
      setLogs(res.logs);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [limit]);

  const sessions = useMemo(() => {
    const grouped = groupBySession(logs);

    return grouped.filter((s) => {
      const okIp = ipFilter ? s.src_ip.includes(ipFilter.trim()) : true;
      const okSid = sidFilter ? s.session_id.includes(sidFilter.trim()) : true;
      const okType = typeFilter
        ? s.event_types.some((t) => t.includes(typeFilter.trim()))
        : true;
      return okIp && okSid && okType;
    });
  }, [logs, ipFilter, sidFilter, typeFilter]);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div
        style={{
          padding: 16,
          borderRadius: 14,
          border: "1px solid #1f2937",
          background: "#111827"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontWeight: 900, fontSize: 18 }}>Sessions</div>
          <div style={{ color: "#a8b0bf", fontSize: 12 }}>
            {loading ? "Loading..." : err ? "Error" : `Loaded ${logs.length} events`}
          </div>
        </div>

        <div style={{ color: "#a8b0bf", fontSize: 12, marginTop: 6 }}>
          Grouped client-side from <code>GET /sessions</code> (mock grouping until backend adds a real sessions endpoint).
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 12 }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={{ color: "#a8b0bf", fontSize: 12, marginBottom: 6 }}>Filter src_ip</div>
            <input
              value={ipFilter}
              onChange={(e) => setIpFilter(e.target.value)}
              placeholder="e.g. 192.168"
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #2a3446",
                background: "#0b1220",
                color: "white"
              }}
            />
          </div>

          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={{ color: "#a8b0bf", fontSize: 12, marginBottom: 6 }}>Filter event_type</div>
            <input
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              placeholder="e.g. ssh"
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #2a3446",
                background: "#0b1220",
                color: "white"
              }}
            />
          </div>

          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={{ color: "#a8b0bf", fontSize: 12, marginBottom: 6 }}>Filter session_id</div>
            <input
              value={sidFilter}
              onChange={(e) => setSidFilter(e.target.value)}
              placeholder="paste session id"
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #2a3446",
                background: "#0b1220",
                color: "white"
              }}
            />
          </div>

          <div style={{ width: 160 }}>
            <div style={{ color: "#a8b0bf", fontSize: 12, marginBottom: 6 }}>Limit</div>
            <input
              type="number"
              min={50}
              max={5000}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #2a3446",
                background: "#0b1220",
                color: "white"
              }}
            />
          </div>

          <div style={{ alignSelf: "end" }}>
            <button
              onClick={() => void load()}
              style={{
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #2a3446",
                background: "#172554",
                color: "white",
                cursor: "pointer",
                fontWeight: 800
              }}
            >
              Refresh
            </button>
          </div>
        </div>

        {err ? (
          <div style={{ marginTop: 12, color: "#a8b0bf" }}>{err}</div>
        ) : null}
      </div>

      <div
        style={{
          padding: 16,
          borderRadius: 14,
          border: "1px solid #1f2937",
          background: "#111827"
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>session_id</th>
              <th style={th}>src_ip</th>
              <th style={th}>events</th>
              <th style={th}>event_types</th>
              <th style={th}>newest</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.session_id}>
                <td style={td}>
                  <Link to={`/sessions/${encodeURIComponent(s.session_id)}`} style={{ color: "#c7d2fe" }}>
                    <span style={pill}>{s.session_id.slice(0, 10)}…</span>
                  </Link>
                  <div style={{ color: "#a8b0bf", fontSize: 12, marginTop: 6, wordBreak: "break-all" }}>
                    {s.session_id}
                  </div>
                </td>

                <td style={td}>
                  <span style={pill}>{s.src_ip}</span>
                </td>

                <td style={td}>{s.count}</td>

                <td style={td}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {s.event_types.map((t) => (
                      <span key={t} style={pill}>
                        {t}
                      </span>
                    ))}
                  </div>
                </td>

                <td style={{ ...td, color: "#a8b0bf" }}>{s.newest_ts || "—"}</td>
              </tr>
            ))}

            {!loading && !err && sessions.length === 0 ? (
              <tr>
                <td style={td} colSpan={5}>
                  <div style={{ color: "#a8b0bf" }}>No sessions match your filters.</div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #1f2937",
  color: "#a8b0bf",
  fontSize: 12
};

const td: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #1f2937",
  verticalAlign: "top"
};

const pill: React.CSSProperties = {
  display: "inline-block",
  padding: "3px 10px",
  borderRadius: 999,
  border: "1px solid #2a3446",
  background: "#0b1220",
  fontSize: 12
};