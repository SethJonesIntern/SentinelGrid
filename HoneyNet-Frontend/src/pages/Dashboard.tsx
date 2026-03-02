import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";

function topN(items: string[], n: number) {
  const m = new Map<string, number>();
  for (const x of items) m.set(x, (m.get(x) ?? 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}

export default function DashboardPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setErr("");
      const res = await api.sessions(200);
      setLogs(res.logs);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, []);

  const derived = useMemo(() => {
    const srcIps = logs.map((l) => l.raw_json?.src_ip ?? "unknown");
    const types = logs.map((l) => l.raw_json?.event_type ?? "unknown");
    const sessions = logs.map((l) => l.raw_json?.session_id ?? "unknown");
    return {
      topIps: topN(srcIps, 5),
      topTypes: topN(types, 5),
      uniqueSessions: new Set(sessions).size
    };
  }, [logs]);

  const newest = logs.slice(0, 15);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 220, padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
          <div style={{ color: "#a8b0bf", fontSize: 12 }}>Recent events loaded</div>
          <div style={{ fontSize: 28, fontWeight: 900 }}>{logs.length}</div>
        </div>
        <div style={{ flex: 1, minWidth: 220, padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
          <div style={{ color: "#a8b0bf", fontSize: 12 }}>Unique session_ids</div>
          <div style={{ fontSize: 28, fontWeight: 900 }}>{derived.uniqueSessions}</div>
        </div>
        <div style={{ flex: 1, minWidth: 220, padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
          <div style={{ color: "#a8b0bf", fontSize: 12 }}>Polling</div>
          <div style={{ fontSize: 28, fontWeight: 900 }}>5s</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 320, padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
          <div style={{ fontWeight: 900 }}>Top Source IPs</div>
          <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
            {derived.topIps.map(([ip, c]) => (
              <div key={ip} style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ padding: "3px 10px", borderRadius: 999, border: "1px solid #2a3446", background: "#0b1220", fontSize: 12 }}>
                  {ip}
                </span>
                <span style={{ color: "#a8b0bf" }}>{c}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 320, padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
          <div style={{ fontWeight: 900 }}>Top Event Types</div>
          <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
            {derived.topTypes.map(([t, c]) => (
              <div key={t} style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ padding: "3px 10px", borderRadius: 999, border: "1px solid #2a3446", background: "#0b1220", fontSize: 12 }}>
                  {t}
                </span>
                <span style={{ color: "#a8b0bf" }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ padding: 16, borderRadius: 14, border: "1px solid #1f2937", background: "#111827" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontWeight: 900 }}>Live Feed (latest)</div>
          <div style={{ color: "#a8b0bf", fontSize: 12 }}>
            {loading ? "Loading..." : err ? "Error" : "OK"}
          </div>
        </div>

        {err ? (
          <div style={{ color: "#a8b0bf", marginTop: 10 }}>{err}</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 10 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>ID</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>timestamp</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>src_ip</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>event_type</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>session_id</th>
              </tr>
            </thead>
            <tbody>
              {newest.map((l) => (
                <tr key={l.id}>
                  <td style={{ padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>{l.id}</td>
                  <td style={{ padding: "10px 12px", borderBottom: "1px solid #1f2937", color: "#a8b0bf" }}>{l.raw_json.timestamp}</td>
                  <td style={{ padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>{l.raw_json.src_ip}</td>
                  <td style={{ padding: "10px 12px", borderBottom: "1px solid #1f2937" }}>{l.raw_json.event_type}</td>
                  <td style={{ padding: "10px 12px", borderBottom: "1px solid #1f2937", color: "#a8b0bf", wordBreak: "break-all" }}>
                    {l.raw_json.session_id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}