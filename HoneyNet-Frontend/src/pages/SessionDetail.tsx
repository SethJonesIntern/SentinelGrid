import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";

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
        
        const res = await api.sessions(1500);
        setLogs(res.logs.filter((l) => l.raw_json.session_id === decoded));
      } catch (e) {
        setErr((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [decoded]);

  const srcIp = logs[0]?.raw_json?.src_ip ?? "unknown";

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div>
            <div style={{ color: "#a8b0bf", fontSize: 12 }}>Session</div>
            <div style={{ fontWeight: 900, wordBreak: "break-all" }}>{decoded}</div>
          </div>
          <Link to="/sessions" style={{ color: "#c7d2fe" }}>← Back</Link>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
          <span style={pill}>src_ip: {srcIp}</span>
          <span style={pill}>events: {logs.length}</span>
          <span style={pill}>status: {loading ? "loading" : err ? "error" : "ok"}</span>
        </div>

        {err ? <div style={{ marginTop: 12, color: "#a8b0bf" }}>{err}</div> : null}
      </div>

      <div style={{ padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>id</th>
              <th style={th}>timestamp</th>
              <th style={th}>event_type</th>
              <th style={th}>sensor_id</th>
              <th style={th}>payload</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td style={td}>{l.id}</td>
                <td style={{ ...td, color: "#a8b0bf" }}>{l.raw_json.timestamp}</td>
                <td style={td}><span style={pill}>{l.raw_json.event_type}</span></td>
                <td style={{ ...td, color: "#a8b0bf" }}>{l.raw_json.sensor_id ?? "—"}</td>
                <td style={td}>
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "#cbd5e1" }}>
                    {JSON.stringify(l.raw_json.payload ?? {}, null, 2)}
                  </pre>
                </td>
              </tr>
            ))}

            {!loading && !err && logs.length === 0 ? (
              <tr>
                <td style={td} colSpan={5}>
                  <div style={{ color: "#a8b0bf" }}>
                    No events found for this session_id within the current fetch limit.
                  </div>
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