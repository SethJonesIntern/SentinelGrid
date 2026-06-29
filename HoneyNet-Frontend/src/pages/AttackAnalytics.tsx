import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip
} from "recharts";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import {
  buildTopIps, buildTopEventTypes, buildTopCommands,
  buildAttacksPerHour, groupBySession
} from "../lib/telemetry";

const COLORS = ["#3b82f6","#22d3ee","#34d399","#f59e0b","#f472b6","#a78bfa","#f87171","#fb923c"];

// ── Tooltip (dark theme, used by every chart) ─────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function DarkTooltip(props: any) {
  const active:  boolean | undefined = props.active;
  const payload: Array<{ name?: unknown; value?: unknown; color?: string; fill?: string }> | undefined = props.payload;
  const label:   unknown = props.label;
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "rgba(4,8,20,0.97)",
      border: "1px solid rgba(59,130,246,0.3)",
      borderRadius: 10,
      padding: "10px 16px",
      fontFamily: "'Space Mono', monospace",
      fontSize: 12,
      boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
    }}>
      {label !== undefined && label !== "" && (
        <div style={{ color: "#6b7a99", marginBottom: 6, fontSize: 11 }}>{String(label)}</div>
      )}
      {payload.map((p, i) => (
        <div key={i} style={{ display:"flex", alignItems:"center", gap:8, marginTop: i > 0 ? 4 : 0 }}>
          <span style={{ width:8, height:8, borderRadius:2, background: p.fill ?? p.color ?? "#3b82f6", flexShrink:0, display:"inline-block" }} />
          <span style={{ color:"#6b7a99" }}>{p.name !== undefined ? String(p.name) : "Value"}:</span>
          <span style={{ color:"#e2e8f4", fontWeight:700 }}>{p.value !== undefined ? String(p.value) : "—"}</span>
        </div>
      ))}
    </div>
  );
}

// ── Extra data builders ───────────────────────────────────────────────────────

const DEPTH_BUCKETS = [
  { range:"1",     label:"Hit & run",      min:1,  max:1,        fill:"#6b7a99" },
  { range:"2–5",   label:"Quick probe",    min:2,  max:5,        fill:"#3b82f6" },
  { range:"6–15",  label:"Exploration",    min:6,  max:15,       fill:"#f59e0b" },
  { range:"16–50", label:"Sustained",      min:16, max:50,       fill:"#f87171" },
  { range:"51+",   label:"Deep intrusion", min:51, max:Infinity, fill:"#dc2626" },
];

function buildSessionDepth(logs: RawLogRow[]) {
  const sessions = groupBySession(logs);
  return DEPTH_BUCKETS.map(b => ({
    range: b.range, label: b.label,
    Sessions: sessions.filter(s => s.count >= b.min && s.count <= b.max).length,
    fill: b.fill,
  }));
}

function buildCredentials(logs: RawLogRow[]) {
  const users: Record<string,number> = {};
  const passes: Record<string,number> = {};
  for (const l of logs) {
    const p  = l.raw_json.payload;
    const u  = p?.username ?? p?.user ?? p?.login;
    const pw = p?.password ?? p?.passwd ?? p?.pass;
    if (u  && typeof u  === "string" && u.length  < 64) users[u]   = (users[u]   ?? 0) + 1;
    if (pw && typeof pw === "string" && pw.length < 64) passes[pw] = (passes[pw] ?? 0) + 1;
  }
  const top = (rec: Record<string,number>, baseHex: string) =>
    Object.entries(rec).sort((a,b)=>b[1]-a[1]).slice(0,7)
      .map(([label, Attempts], i) => ({
        label, Attempts,
        fill: `${baseHex}${Math.round(220 - i * 22).toString(16).padStart(2,"0")}`,
      }));
  return { usernames: top(users,"#22d3ee"), passwords: top(passes,"#f59e0b") };
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AttackAnalyticsPage() {
  const [logs, setLogs]       = useState<RawLogRow[]>([]);
  const [err, setErr]         = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try { setErr(""); const res = await api.logs(500); setLogs(res.logs); }
    catch (e) { setErr((e as Error).message); }
    finally   { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  const timeline     = useMemo(() => buildAttacksPerHour(logs).slice(-24), [logs]);
  const topEvents    = useMemo(() => buildTopEventTypes(logs, 8), [logs]);
  const topIps       = useMemo(() => buildTopIps(logs, 8), [logs]);
  const topCommands  = useMemo(() => buildTopCommands(logs, 8), [logs]);
  const sessionDepth = useMemo(() => buildSessionDepth(logs), [logs]);
  const creds        = useMemo(() => buildCredentials(logs), [logs]);

  // Enrich with fill colours (Recharts v3: fill in data, not Cell)
  const topEventsWithFill  = useMemo(() =>
    topEvents.map((e, i) => ({ ...e, fill: COLORS[i % COLORS.length] })), [topEvents]);

  const topIpsWithFill = useMemo(() =>
    topIps.map((item, i) => ({
      ...item,
      fill: i === 0 ? "#f87171" : `rgba(59,130,246,${(0.9 - i * 0.08).toFixed(2)})`,
    })), [topIps]);

  const topCommandsWithFill = useMemo(() =>
    topCommands.map((c, i) => ({ ...c, fill: COLORS[(i + 2) % COLORS.length] })), [topCommands]);

  const uniqueIps   = new Set(logs.map(l => l.raw_json.src_ip)).size;
  const totalEvents = logs.length;
  const sessions    = groupBySession(logs).length;
  const deepCount   = sessionDepth.find(d => d.range === "51+")?.Sessions ?? 0;
  const totalForPct = topEventsWithFill.reduce((s, e) => s + e.value, 0);

  const depthEmpty  = sessionDepth.every(d => d.Sessions === 0);
  const credsEmpty  = creds.usernames.length === 0 && creds.passwords.length === 0;

  return (
    <div style={{ display:"grid", gap:16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Attack Analytics</div>
            <div style={subtle}>
              {totalEvents.toLocaleString()} events · {uniqueIps} attacking IPs · {sessions} sessions
            </div>
          </div>
          <button onClick={() => void load()} style={btn}>{loading ? "Loading…" : "↺ Refresh"}</button>
        </div>
        {err && <div style={{ ...subtle, color:"#f87171", marginTop:8 }}>{err}</div>}
      </div>

      {/* KPIs */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:12 }}>
        <KPI label="Total Events"    value={totalEvents.toLocaleString()} accent="#3b82f6" />
        <KPI label="Attacking IPs"   value={String(uniqueIps)}           accent="#f87171" />
        <KPI label="Sessions"        value={String(sessions)}            accent="#22d3ee" />
        <KPI label="Deep Intrusions" value={String(deepCount)}           accent="#dc2626" note="50+ events" />
        <KPI label="Attack Types"    value={String(topEvents.length)}    accent="#a78bfa" />
      </div>

      {/* ── Attack Timeline (full width) ────────────────────────────────────── */}
      <div style={panel}>
        <div style={{ marginBottom:16 }}>
          <div style={cardTitle}>Attack Volume Over Time</div>
          <div style={{ ...subtle, marginTop:4 }}>
            Events captured per hour — peaks show when attackers are most active
          </div>
        </div>
        {timeline.length < 2
          ? <Empty msg="Not enough data yet — need events across at least two hours." />
          : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={timeline} margin={{ top:8, right:16, left:-20, bottom:0 }}>
                <defs>
                  <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                <Tooltip content={(p) => <DarkTooltip {...p} />} />
                <Area type="monotone" dataKey="value" name="Events"
                  stroke="#3b82f6" strokeWidth={2} fill="url(#blueGrad)"
                  dot={false} activeDot={{ r:5, fill:"#60a5fa", strokeWidth:0 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
      </div>

      {/* ── Three-column charts ─────────────────────────────────────────────── */}
      <div style={threeCol}>

        {/* Event type donut */}
        <div style={panel}>
          <div style={{ marginBottom:14 }}>
            <div style={cardTitle}>What Types of Attacks?</div>
            <div style={{ ...subtle, marginTop:4 }}>Breakdown of event categories</div>
          </div>
          {loading ? <Empty msg="Loading…" /> : topEventsWithFill.length === 0 ? <Empty /> : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={topEventsWithFill}
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
              <div style={{ display:"grid", gap:5, marginTop:8 }}>
                {topEventsWithFill.slice(0, 5).map(e => {
                  const pct = totalForPct > 0 ? Math.round((e.value / totalForPct) * 100) : 0;
                  return (
                    <div key={e.label} style={{ display:"flex", alignItems:"center", gap:8, fontSize:11 }}>
                      <span style={{ width:8, height:8, borderRadius:2, background:e.fill, flexShrink:0 }} />
                      <span style={{ color:"#8896b0", flex:1, fontFamily:"'Space Mono',monospace", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                        {e.label}
                      </span>
                      <span style={{ color:"#4b5f7c", fontSize:10, minWidth:28, textAlign:"right" }}>{pct}%</span>
                      <span style={{ color:e.fill, fontWeight:700, minWidth:24, textAlign:"right" }}>{e.value}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Top IPs */}
        <div style={panel}>
          <div style={{ marginBottom:14 }}>
            <div style={cardTitle}>Who Is Attacking?</div>
            <div style={{ ...subtle, marginTop:4 }}>Most active source IPs by event count</div>
          </div>
          {loading ? <Empty msg="Loading…" /> : topIpsWithFill.length === 0 ? <Empty /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topIpsWithFill} layout="vertical" margin={{ top:0, right:36, left:0, bottom:0 }}>
                <XAxis type="number" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="label" width={118}
                  tick={{ fill:"#8896b0", fontSize:10, fontFamily:"'Space Mono',monospace" }}
                  axisLine={false} tickLine={false} />
                <Tooltip content={(p) => <DarkTooltip {...p} />} />
                <Bar dataKey="value" name="Events" radius={[0,4,4,0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top commands */}
        <div style={panel}>
          <div style={{ marginBottom:14 }}>
            <div style={cardTitle}>Commands Attackers Ran</div>
            <div style={{ ...subtle, marginTop:4 }}>Commands typed in honeypot sessions</div>
          </div>
          {loading ? <Empty msg="Loading…" /> : topCommandsWithFill.length === 0
            ? <Empty msg="No commands yet — will appear once SSH sessions are active." />
            : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={topCommandsWithFill.map(c => ({
                    ...c,
                    label: c.label.length > 22 ? c.label.slice(0, 22) + "…" : c.label,
                  }))}
                  layout="vertical"
                  margin={{ top:0, right:36, left:0, bottom:0 }}
                >
                  <XAxis type="number" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="label" width={134}
                    tick={{ fill:"#8896b0", fontSize:10, fontFamily:"'Space Mono',monospace" }}
                    axisLine={false} tickLine={false} />
                  <Tooltip content={(p) => <DarkTooltip {...p} />} />
                  <Bar dataKey="value" name="Times run" radius={[0,4,4,0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
            )}
        </div>
      </div>

      {/* ── Session depth + Credentials ─────────────────────────────────────── */}
      <div style={twoCol}>

        {/* Session depth */}
        <div style={panel}>
          <div style={{ marginBottom:14 }}>
            <div style={cardTitle}>How Long Do Attackers Stay?</div>
            <div style={{ ...subtle, marginTop:4 }}>
              Sessions grouped by event count — left = quick scan, right = determined attacker
            </div>
          </div>
          {loading ? <Empty msg="Loading…" /> : depthEmpty ? <Empty /> : (
            <>
              <ResponsiveContainer width="100%" height={190}>
                <BarChart data={sessionDepth} margin={{ top:8, right:12, left:-20, bottom:4 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="range" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                  <Tooltip content={(p) => <DarkTooltip {...p} />} />
                  <Bar dataKey="Sessions" radius={[4,4,0,0]} maxBarSize={56} />
                </BarChart>
              </ResponsiveContainer>
              <div style={{ display:"flex", gap:10, marginTop:10, flexWrap:"wrap" }}>
                {DEPTH_BUCKETS.map(b => (
                  <div key={b.range} style={{ display:"flex", alignItems:"center", gap:5, fontSize:10 }}>
                    <span style={{ width:8, height:8, borderRadius:2, background:b.fill, display:"inline-block" }} />
                    <span style={{ color:"#6b7a99" }}>{b.label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Credentials */}
        <div style={panel}>
          <div style={{ marginBottom:14 }}>
            <div style={cardTitle}>What Credentials Are Being Tried?</div>
            <div style={{ ...subtle, marginTop:4 }}>
              Usernames and passwords from login attempts — shows attacker wordlists
            </div>
          </div>
          {loading ? <Empty msg="Loading…" /> : credsEmpty
            ? <Empty msg="No credential data yet — appears when login events include username/password fields." />
            : (
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
                <div>
                  <div style={{ fontSize:10, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase", color:"#22d3ee", marginBottom:10 }}>
                    Usernames
                  </div>
                  {creds.usernames.length === 0
                    ? <div style={{ color:"#3d4f6e", fontSize:11 }}>None captured</div>
                    : (
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={creds.usernames} layout="vertical" margin={{ top:0, right:16, bottom:0, left:0 }}>
                          <XAxis type="number" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                          <YAxis type="category" dataKey="label" width={70}
                            tick={{ fill:"#8896b0", fontSize:10, fontFamily:"'Space Mono',monospace" }}
                            axisLine={false} tickLine={false} />
                          <Tooltip content={(p) => <DarkTooltip {...p} />} />
                          <Bar dataKey="Attempts" radius={[0,4,4,0]} maxBarSize={16} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                </div>
                <div>
                  <div style={{ fontSize:10, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase", color:"#f59e0b", marginBottom:10 }}>
                    Passwords
                  </div>
                  {creds.passwords.length === 0
                    ? <div style={{ color:"#3d4f6e", fontSize:11 }}>None captured</div>
                    : (
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={creds.passwords} layout="vertical" margin={{ top:0, right:16, bottom:0, left:0 }}>
                          <XAxis type="number" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false} />
                          <YAxis type="category" dataKey="label" width={70}
                            tick={{ fill:"#8896b0", fontSize:10, fontFamily:"'Space Mono',monospace" }}
                            axisLine={false} tickLine={false} />
                          <Tooltip content={(p) => <DarkTooltip {...p} />} />
                          <Bar dataKey="Attempts" radius={[0,4,4,0]} maxBarSize={16} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function KPI({ label, value, accent, note }: { label:string; value:string; accent:string; note?:string }) {
  return (
    <div style={{ ...panel, position:"relative", overflow:"hidden" }}>
      <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,${accent},transparent)` }} />
      <div style={subtle}>{label}</div>
      <div style={{ fontSize:26, fontWeight:900, marginTop:4, color:accent, lineHeight:1 }}>{value}</div>
      {note && <div style={{ ...subtle, marginTop:4, fontSize:10 }}>{note}</div>}
    </div>
  );
}

function Empty({ msg }: { msg?: string }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"28px 0", color:"#3d4f6e", fontSize:12 }}>
      <span>◉</span>
      <span style={{ lineHeight:1.5 }}>{msg ?? "No data yet — events will appear automatically."}</span>
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const panel: React.CSSProperties = {
  background: "rgba(6,10,24,0.7)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid rgba(255,255,255,0.08)",
  boxShadow: "0 0 40px rgba(59,130,246,0.08), inset 0 1px 0 rgba(255,255,255,0.04)",
  borderRadius: 14,
  padding: "20px 24px",
};
const pageTitle: React.CSSProperties = { fontSize:22, fontWeight:900, letterSpacing:"0.02em", color:"#e2e8f4" };
const cardTitle: React.CSSProperties = { fontSize:13, fontWeight:700, color:"#c8d3e8", letterSpacing:"0.01em" };
const subtle:    React.CSSProperties = { color:"#6b7a99", fontSize:12 };
const topRow:    React.CSSProperties = { display:"flex", justifyContent:"space-between", alignItems:"center", gap:12, flexWrap:"wrap" };
const threeCol:  React.CSSProperties = { display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:12 };
const twoCol:    React.CSSProperties = { display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(420px,1fr))", gap:16 };
const btn:       React.CSSProperties = { padding:"8px 18px", borderRadius:9, border:"1px solid rgba(99,165,255,0.3)", background:"rgba(59,130,246,0.12)", color:"#93c5fd", cursor:"pointer", fontWeight:700, fontSize:13, fontFamily:"inherit" };
