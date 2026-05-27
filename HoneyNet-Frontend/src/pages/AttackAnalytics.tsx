import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  BarChart, Bar, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  CartesianGrid, ReferenceLine
} from "recharts";
import { api } from "../lib/api";
import type { RawLogRow } from "../lib/api";
import { buildTopEventTypes } from "../lib/telemetry";

const TT = {
  contentStyle: {
    background: "rgba(4,8,20,0.97)",
    border: "1px solid rgba(59,130,246,0.25)",
    borderRadius: 10, color: "#e2e8f4", fontSize: 12,
    fontFamily: "'Space Mono', monospace",
    boxShadow: "0 0 20px rgba(59,130,246,0.1)",
  },
  labelStyle: { color: "#4b5f7c", marginBottom: 4 },
  cursor: { stroke: "rgba(59,130,246,0.2)", strokeWidth: 1 },
};

function buildSeverityTimeline(logs: RawLogRow[]) {
  const HIGH = ["exploit","injection","rce","shell","exec","cmd","root","sudo"];
  const MED  = ["login","auth","scan","probe","brute","fuzz"];
  const buckets: Record<string, { hour: string; high: number; medium: number; low: number }> = {};
  for (const l of logs) {
    const d = new Date(l.raw_json.timestamp);
    if (isNaN(d.getTime())) continue;
    const hour = `${String(d.getHours()).padStart(2,"0")}:00`;
    if (!buckets[hour]) buckets[hour] = { hour, high: 0, medium: 0, low: 0 };
    const combined = ((l.raw_json.event_type ?? "") + (l.raw_json.payload?.command ?? "")).toLowerCase();
    if (HIGH.some(k => combined.includes(k))) buckets[hour].high++;
    else if (MED.some(k => combined.includes(k))) buckets[hour].medium++;
    else buckets[hour].low++;
  }
  return Object.values(buckets).slice(-20);
}

function buildUniqueIpPerHour(logs: RawLogRow[]) {
  const seen: Record<string, Set<string>> = {};
  for (const l of logs) {
    const d = new Date(l.raw_json.timestamp);
    if (isNaN(d.getTime())) continue;
    const hour = `${String(d.getHours()).padStart(2,"0")}:00`;
    if (!seen[hour]) seen[hour] = new Set();
    seen[hour].add(l.raw_json.src_ip);
  }
  return Object.entries(seen).map(([hour, ips]) => ({ hour, unique: ips.size })).slice(-12);
}

function buildProtocolRadar(logs: RawLogRow[]) {
  const counts: Record<string, number> = { SSH: 0, HTTP: 0, FTP: 0, Telnet: 0, RDP: 0, SMTP: 0 };
  for (const l of logs) {
    const et = (l.raw_json.event_type ?? "").toLowerCase();
    const port = l.raw_json.payload?.port ?? 0;
    if (et.includes("ssh") || port === 22) counts.SSH++;
    else if (et.includes("http") || port === 80 || port === 443) counts.HTTP++;
    else if (et.includes("ftp") || port === 21) counts.FTP++;
    else if (et.includes("telnet") || port === 23) counts.Telnet++;
    else if (et.includes("rdp") || port === 3389) counts.RDP++;
    else if (et.includes("smtp") || port === 25) counts.SMTP++;
    else counts.SSH++;
  }
  const max = Math.max(...Object.values(counts), 1);
  return Object.entries(counts).map(([proto, count]) => ({ proto, value: Math.round((count / max) * 100), count }));
}

function buildThreatMatrix(logs: RawLogRow[]) {
  const HIGH = ["exploit","inject","shell","exec","rce","cmd"];
  const ipMap: Record<string, { count: number; high: number }> = {};
  for (const l of logs) {
    const ip = l.raw_json.src_ip;
    if (!ipMap[ip]) ipMap[ip] = { count: 0, high: 0 };
    ipMap[ip].count++;
    const combined = ((l.raw_json.event_type ?? "") + (l.raw_json.payload?.command ?? "")).toLowerCase();
    if (HIGH.some(k => combined.includes(k))) ipMap[ip].high++;
  }
  return Object.entries(ipMap)
    .sort((a, b) => b[1].count - a[1].count).slice(0, 8)
    .map(([ip, d]) => ({
      ip, total: d.count, high: d.high, low: d.count - d.high,
      threat: d.high > 0 ? "HIGH" : d.count > 10 ? "MED" : "LOW",
    }));
}

function buildCommandFrequency(logs: RawLogRow[]) {
  const cmds: Record<string, number> = {};
  for (const l of logs) {
    const cmd = l.raw_json.payload?.command ?? l.raw_json.payload?.input ?? "";
    if (!cmd) continue;
    const short = String(cmd).split(" ")[0].slice(0, 20);
    cmds[short] = (cmds[short] ?? 0) + 1;
  }
  return Object.entries(cmds).sort((a,b) => b[1]-a[1]).slice(0,8).map(([cmd,count]) => ({ cmd, count }));
}

export default function AttackAnalyticsPage() {
  const [logs, setLogs] = useState<RawLogRow[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try { setErr(""); const res = await api.logs(500); setLogs(res.logs); }
    catch (e) { setErr((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  const severityTimeline = useMemo(() => buildSeverityTimeline(logs), [logs]);
  const uniqueIpPerHour  = useMemo(() => buildUniqueIpPerHour(logs), [logs]);
  const protocolRadar    = useMemo(() => buildProtocolRadar(logs), [logs]);
  const threatMatrix     = useMemo(() => buildThreatMatrix(logs), [logs]);
  const cmdFrequency     = useMemo(() => buildCommandFrequency(logs), [logs]);
  const topEvents        = useMemo(() => buildTopEventTypes(logs, 6), [logs]);

  const highCount  = severityTimeline.reduce((s,r) => s+r.high, 0);
  const uniqueIps  = new Set(logs.map(l => l.raw_json.src_ip)).size;
  const avgPerHour = severityTimeline.length ? Math.round(logs.length / severityTimeline.length) : 0;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Attack Analytics</div>
            <div style={subtle}>Threat intelligence across {logs.length} captured events.</div>
          </div>
          <button onClick={() => void load()} style={btn}>{loading ? "Loading..." : "↺ Refresh"}</button>
        </div>
        {err && <div style={{ ...subtle, color: "#f87171", marginTop: 8 }}>{err}</div>}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <KPI label="Total Events"     value={String(logs.length)} accent="#3b82f6" icon="⬡" />
        <KPI label="High Severity"    value={String(highCount)}   accent="#f87171" icon="▲" />
        <KPI label="Unique IPs"       value={String(uniqueIps)}   accent="#f59e0b" icon="◎" />
        <KPI label="Avg Events / Hr"  value={String(avgPerHour)}  accent="#22d3ee" icon="∿" />
        <KPI label="Event Types"      value={String(topEvents.length)} accent="#a78bfa" icon="◈" />
      </div>

      <div style={twoCol}>
        <Card title="Threat Severity Timeline" sub="HIGH / MED / LOW events stacked per hour" loading={loading} empty={severityTimeline.length===0}>
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={severityTimeline} margin={{ top:8, right:8, left:-22, bottom:0 }}>
              <defs>
                <linearGradient id="gH" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f87171" stopOpacity={0.4}/><stop offset="95%" stopColor="#f87171" stopOpacity={0}/></linearGradient>
                <linearGradient id="gM" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/><stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/></linearGradient>
                <linearGradient id="gL" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false}/>
              <XAxis dataKey="hour" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false}/>
              <Tooltip {...TT}/>
              <Area type="monotone" dataKey="low"    stroke="#3b82f6" strokeWidth={1.5} fill="url(#gL)" name="Low"  stackId="1"/>
              <Area type="monotone" dataKey="medium" stroke="#f59e0b" strokeWidth={1.5} fill="url(#gM)" name="Med"  stackId="1"/>
              <Area type="monotone" dataKey="high"   stroke="#f87171" strokeWidth={2}   fill="url(#gH)" name="High" stackId="1"/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card title="IP Surge Detection" sub="New unique source IPs per hour — spikes = coordinated attacks" loading={loading} empty={uniqueIpPerHour.length===0}>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={uniqueIpPerHour} margin={{ top:8, right:8, left:-22, bottom:0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false}/>
              <XAxis dataKey="hour" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false}/>
              <Tooltip {...TT}/>
              {uniqueIpPerHour.length > 0 && (
                <ReferenceLine
                  y={Math.round(uniqueIpPerHour.reduce((s,r)=>s+r.unique,0)/uniqueIpPerHour.length)}
                  stroke="rgba(251,191,36,0.35)" strokeDasharray="4 4"
                  label={{ value:"avg", fill:"#4b5f7c", fontSize:9 }}
                />
              )}
              <Bar dataKey="unique" name="Unique IPs" radius={[4,4,0,0]}>
                {uniqueIpPerHour.map((entry, i) => {
                  const avg = uniqueIpPerHour.reduce((s,r)=>s+r.unique,0)/uniqueIpPerHour.length;
                  return <Cell key={i} fill={entry.unique > avg*1.5 ? "#f87171" : "#3b82f6"}/>;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div style={twoCol}>
        <Card title="Attack Vector Breakdown" sub="Protocol distribution across all honeypot sessions" loading={loading} empty={false}>
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            <ResponsiveContainer width="55%" height={220}>
              <RadarChart data={protocolRadar} margin={{ top:10, right:20, left:20, bottom:10 }}>
                <PolarGrid stroke="rgba(59,130,246,0.15)"/>
                <PolarAngleAxis dataKey="proto" tick={{ fill:"#6b7a99", fontSize:10 }}/>
                <Radar name="Activity" dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.15} strokeWidth={1.5}/>
                <Tooltip {...TT} formatter={(_v: number, _n: string, p: any) => [p.payload.count, "events"]}/>
              </RadarChart>
            </ResponsiveContainer>
            <div style={{ flex:1, display:"grid", gap:9 }}>
              {protocolRadar.map(p => (
                <div key={p.proto} style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <span style={{ width:40, fontSize:10, color:"#4b5f7c", fontFamily:"'Space Mono',monospace" }}>{p.proto}</span>
                  <div style={{ flex:1, height:4, borderRadius:2, background:"rgba(255,255,255,0.05)", overflow:"hidden" }}>
                    <div style={{ width:`${p.value}%`, height:"100%", background:"linear-gradient(90deg,#22d3ee,#3b82f6)", borderRadius:2 }}/>
                  </div>
                  <span style={{ fontSize:10, color:"#22d3ee", fontFamily:"'Space Mono',monospace", minWidth:24, textAlign:"right" }}>{p.count}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Attacker Threat Matrix" sub="Source IPs by volume and detected severity level" loading={loading} empty={threatMatrix.length===0}>
          <div style={{ display:"grid", gap:9 }}>
            {threatMatrix.map(row => {
              const tc = row.threat==="HIGH" ? "#f87171" : row.threat==="MED" ? "#f59e0b" : "#34d399";
              const maxT = threatMatrix[0]?.total ?? 1;
              return (
                <div key={row.ip} style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <span style={{ fontSize:9, fontWeight:700, padding:"2px 6px", borderRadius:4, border:`1px solid ${tc}40`, color:tc, background:`${tc}12`, fontFamily:"'Space Mono',monospace", minWidth:34, textAlign:"center" }}>{row.threat}</span>
                  <span style={{ fontSize:11, color:"#8896b0", fontFamily:"'Space Mono',monospace", minWidth:110, flexShrink:0 }}>{row.ip}</span>
                  <div style={{ flex:1, height:6, borderRadius:3, background:"rgba(255,255,255,0.05)", overflow:"hidden", display:"flex" }}>
                    <div style={{ width:`${(row.high/maxT)*100}%`, background:"#f87171", height:"100%" }}/>
                    <div style={{ width:`${(row.low/maxT)*100}%`, background:"#3b82f6", height:"100%" }}/>
                  </div>
                  <span style={{ fontSize:11, color:"#e2e8f4", fontFamily:"'Space Mono',monospace", minWidth:28, textAlign:"right" }}>{row.total}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div style={twoCol}>
        <Card title="Shell Command Frequency" sub="Most executed commands inside honeypot sessions" loading={loading} empty={cmdFrequency.length===0}>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={cmdFrequency} layout="vertical" margin={{ top:0, right:20, left:10, bottom:0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" horizontal={false}/>
              <XAxis type="number" tick={{ fill:"#4b5f7c", fontSize:9 }} axisLine={false} tickLine={false}/>
              <YAxis type="category" dataKey="cmd" tick={{ fill:"#a8b5cc", fontSize:10, fontFamily:"'Space Mono',monospace" }} axisLine={false} tickLine={false} width={80}/>
              <Tooltip {...TT}/>
              <Bar dataKey="count" name="Executions" radius={[0,4,4,0]}>
                {cmdFrequency.map((_,i) => <Cell key={i} fill={`rgba(52,211,153,${0.9-i*0.09})`}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Event Type Distribution" sub="Proportion of event categories observed across all sessions" loading={loading} empty={topEvents.length===0}>
          <div style={{ display:"grid", gap:11, paddingTop:6 }}>
            {topEvents.map((ev, i) => {
              const colors = ["#3b82f6","#22d3ee","#f59e0b","#f87171","#a78bfa","#34d399"];
              const color = colors[i%6];
              const pct = Math.round((ev.value/Math.max(logs.length,1))*100);
              return (
                <div key={ev.label}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                    <span style={{ fontSize:11, color:"#c8d3e8", fontFamily:"'Space Mono',monospace" }}>{ev.label}</span>
                    <span style={{ fontSize:11, color, fontFamily:"'Space Mono',monospace" }}>{ev.value} <span style={{ color:"#4b5f7c" }}>({pct}%)</span></span>
                  </div>
                  <div style={{ height:5, borderRadius:3, background:"rgba(255,255,255,0.05)", overflow:"hidden" }}>
                    <div style={{ width:`${(ev.value/Math.max(topEvents[0]?.value,1))*100}%`, height:"100%", background:`linear-gradient(90deg,${color},${color}88)`, borderRadius:3, transition:"width 0.6s ease" }}/>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}

function KPI({ label, value, accent, icon }: { label:string; value:string; accent:string; icon:string }) {
  return (
    <div style={{ ...panel, position:"relative", overflow:"hidden" }}>
      <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,${accent},transparent)` }}/>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
        <div>
          <div style={subtle}>{label}</div>
          <div style={{ fontSize:26, fontWeight:900, marginTop:4, color:accent, lineHeight:1 }}>{value}</div>
        </div>
        <div style={{ fontSize:18, color:`${accent}50` }}>{icon}</div>
      </div>
    </div>
  );
}

function Card({ title, sub, loading, empty, children }: { title:string; sub:string; loading:boolean; empty:boolean; children:React.ReactNode }) {
  return (
    <div style={panel}>
      <div style={{ marginBottom:14 }}>
        <div style={sectionLabel}>{title}</div>
        <div style={{ ...subtle, marginTop:3 }}>{sub}</div>
      </div>
      {loading ? (
        <div style={emptyStyle}><span style={{ color:"#2a3a52" }}>◌</span> Loading telemetry...</div>
      ) : empty ? (
        <div style={emptyStyle}><span style={{ color:"#2a3a52" }}>◉</span> No data yet — events will populate this chart automatically.</div>
      ) : children}
    </div>
  );
}

const panel: React.CSSProperties = { background:"rgba(6,10,24,0.7)", backdropFilter:"blur(20px)", WebkitBackdropFilter:"blur(20px)", border:"1px solid rgba(255,255,255,0.08)", boxShadow:"0 0 40px rgba(59,130,246,0.08),inset 0 1px 0 rgba(255,255,255,0.04)", borderRadius:14, padding:"20px 24px" };
const pageTitle: React.CSSProperties = { fontSize:22, fontWeight:900, letterSpacing:"0.02em", color:"#e2e8f4" };
const sectionLabel: React.CSSProperties = { fontSize:11, fontWeight:700, letterSpacing:"0.12em", textTransform:"uppercase", color:"#4b5f7c" };
const subtle: React.CSSProperties = { color:"#6b7a99", fontSize:12 };
const emptyStyle: React.CSSProperties = { color:"#3d4f6e", fontSize:12, display:"flex", alignItems:"center", gap:10, padding:"40px 0" };
const topRow: React.CSSProperties = { display:"flex", justifyContent:"space-between", alignItems:"center", gap:12, flexWrap:"wrap" };
const twoCol: React.CSSProperties = { display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(400px,1fr))", gap:16 };
const btn: React.CSSProperties = { padding:"8px 18px", borderRadius:9, border:"1px solid rgba(99,165,255,0.3)", background:"rgba(59,130,246,0.12)", color:"#93c5fd", cursor:"pointer", fontWeight:700, fontSize:13, fontFamily:"inherit" };