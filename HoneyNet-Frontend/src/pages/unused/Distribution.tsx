import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, XAxis, YAxis, Tooltip
} from "recharts";
import { api } from "../../lib/api";
import type { RawLogRow } from "../../lib/api";
import { buildHoneypotDistribution } from "../../lib/telemetry";


const FETCH_LIMIT = 50000;

const TYPE_COLORS: Record<string, string> = {
  SSH: "#3b82f6",
  HTTP: "#22d3ee",
  Redis: "#f87171",
  MySQL: "#f59e0b",
  FTP: "#a78bfa",
  SMTP: "#34d399",
  Other: "#6b7a99"
};


function DarkTooltip(props: any) {
  const active: boolean | undefined = props.active;
  const payload: Array<{ name?: unknown; value?: unknown; color?: string; fill?: string }> | undefined = props.payload;
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "rgba(4,8,20,0.97)",
      border: "1px solid rgba(59,130,246,0.3)",
      borderRadius: 10,
      padding: "10px 16px",
      fontFamily: "'Space Mono', monospace",
      fontSize: 12,
      boxShadow: "0 8px 32px rgba(0,0,0,0.6)"
    }}>
      {payload.map((p, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginTop: i > 0 ? 4 : 0 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.fill ?? p.color ?? "#3b82f6", flexShrink: 0, display: "inline-block" }} />
          <span style={{ color: "#6b7a99" }}>{p.name !== undefined ? String(p.name) : "Value"}:</span>
          <span style={{ color: "#e2e8f4", fontWeight: 700 }}>{p.value !== undefined ? String(p.value) : "—"}</span>
        </div>
      ))}
    </div>
  );
}

export default function DistributionPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setErr("");
      const res = await api.logs(FETCH_LIMIT);
      setLogs(res.logs);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void load(); }, []);

  const distribution = useMemo(() => buildHoneypotDistribution(logs), [logs]);
  const distributionWithFill = useMemo(
    () => distribution.map((p) => ({ ...p, fill: TYPE_COLORS[p.label] ?? "#6b7a99" })),
    [distribution]
  );
  const total = distribution.reduce((s, p) => s + p.value, 0);

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Honeypot Distribution</div>
          </div>
          <button onClick={() => void load()} style={btn}>{loading ? "Loading…" : "↺ Refresh"}</button>
        </div>
        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 8 }}>{err}</div>}
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12 }}>
        {distribution.map((p) => (
          <KPI key={p.label} label={`${p.label} Events`} value={p.value.toLocaleString()} accent={TYPE_COLORS[p.label] ?? "#6b7a99"} />
        ))}
        {distribution.length === 0 && (
          <KPI label="Events" value="0" accent="#6b7a99" />
        )}
      </div>

      <div style={twoCol}>

        {/* Bar chart — absolute counts */}
        <div style={panel}>
          <div style={{ marginBottom: 14 }}>
            <div style={cardTitle}>Events by Honeypot Type</div>
            <div style={{ ...subtle, marginTop: 4 }}>How many events each honeypot type has captured</div>
          </div>
          {loading ? <Empty msg="Loading…" /> : distributionWithFill.length === 0 ? <Empty /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={distributionWithFill} layout="vertical" margin={{ top: 0, right: 36, left: 0, bottom: 0 }}>
                <XAxis type="number" tick={{ fill: "#4b5f7c", fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="label" width={70}
                  tick={{ fill: "#8896b0", fontSize: 11, fontFamily: "'Space Mono',monospace" }}
                  axisLine={false} tickLine={false} />
                <Tooltip content={(p) => <DarkTooltip {...p} />} />
                <Bar dataKey="value" name="Events" radius={[0, 4, 4, 0]} maxBarSize={36} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* proportions */}
        <div style={panel}>
          <div style={{ marginBottom: 14 }}>
            <div style={cardTitle}>Distribution Share</div>
            <div style={{ ...subtle, marginTop: 4 }}>Proportion of traffic per honeypot type</div>
          </div>
          {loading ? <Empty msg="Loading…" /> : distributionWithFill.length === 0 ? <Empty /> : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={distributionWithFill}
                    dataKey="value"
                    nameKey="label"
                    cx="50%" cy="50%"
                    innerRadius={52} outerRadius={78}
                    paddingAngle={3}
                    strokeWidth={0}
                  />
                  <Tooltip content={(p) => <DarkTooltip {...p} />} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: "grid", gap: 5, marginTop: 8 }}>
                {distributionWithFill.map((p) => {
                  const pct = total > 0 ? Math.round((p.value / total) * 100) : 0;
                  return (
                    <div key={p.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: p.fill, flexShrink: 0 }} />
                      <span style={{ color: "#8896b0", flex: 1, fontFamily: "'Space Mono',monospace" }}>{p.label}</span>
                      <span style={{ color: "#4b5f7c", fontSize: 10, minWidth: 28, textAlign: "right" }}>{pct}%</span>
                      <span style={{ color: p.fill, fontWeight: 700, minWidth: 24, textAlign: "right" }}>{p.value}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function KPI({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ ...panel, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,${accent},transparent)` }} />
      <div style={subtle}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 900, marginTop: 4, color: accent, lineHeight: 1 }}>{value}</div>
    </div>
  );
}

function Empty({ msg }: { msg?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "28px 0", color: "#3d4f6e", fontSize: 12 }}>
      <span>◉</span>
      <span style={{ lineHeight: 1.5 }}>{msg ?? "No data yet — events will appear automatically."}</span>
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
const pageTitle: React.CSSProperties = { fontSize: 22, fontWeight: 900, letterSpacing: "0.02em", color: "#e2e8f4" };
const cardTitle: React.CSSProperties = { fontSize: 13, fontWeight: 700, color: "#c8d3e8", letterSpacing: "0.01em" };
const subtle: React.CSSProperties = { color: "#6b7a99", fontSize: 12 };
const topRow: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" };
const twoCol: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(420px,1fr))", gap: 16 };
const btn: React.CSSProperties = { padding: "8px 18px", borderRadius: 9, border: "1px solid rgba(99,165,255,0.3)", background: "rgba(59,130,246,0.12)", color: "#93c5fd", cursor: "pointer", fontWeight: 700, fontSize: 13, fontFamily: "inherit" };
