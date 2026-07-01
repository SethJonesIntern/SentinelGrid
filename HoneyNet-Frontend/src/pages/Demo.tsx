import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { HONEYPOT_TYPES, TYPE_COLORS, TYPE_LABELS } from "../lib/honeynet";
import RaceBarChart from "../components/RaceBarChart";

const COOLDOWN_MS = 10 * 60 * 1000;
const LAST_REDISTRIBUTED_KEY = "sg_redistribute_last_at";

function formatCountdown(ms: number): string {
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function timeAgo(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}


function orderedTypes(counts: Record<string, number>): string[] {
  const known = HONEYPOT_TYPES.filter((hp) => hp in counts);
  const unknown = Object.keys(counts).filter((hp) => !HONEYPOT_TYPES.includes(hp as never));
  return [...known, ...unknown];
}

export default function DemoPage() {
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [loadingState, setLoadingState] = useState(true);
  const [stateErr, setStateErr] = useState("");
  const [redistributing, setRedistributing] = useState(false);
  const [redistributeErr, setRedistributeErr] = useState("");
  const [lastRedistributedAt, setLastRedistributedAt] = useState<number | null>(() => {
    const stored = localStorage.getItem(LAST_REDISTRIBUTED_KEY);
    return stored ? Number(stored) : null;
  });
  const [now, setNow] = useState(() => Date.now());

  async function loadState() {
    try {
      setStateErr("");
      const res = await api.ml.state();
      setCounts(res.counts);
    } catch (e) {
      setStateErr((e as Error).message);
    } finally {
      setLoadingState(false);
    }
  }
  useEffect(() => { void loadState(); }, []);

  const cooldownRemaining = lastRedistributedAt !== null
    ? Math.max(0, lastRedistributedAt + COOLDOWN_MS - now)
    : 0;
  const onCooldown = cooldownRemaining > 0;

  useEffect(() => {
    if (!onCooldown) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [onCooldown]);

  async function handleRedistribute() {
    if (onCooldown || redistributing) return;
    setRedistributing(true);
    try {
      setRedistributeErr("");
      const res = await api.ml.redistribute();
      setCounts(res.counts);
      const ts = Date.now();
      localStorage.setItem(LAST_REDISTRIBUTED_KEY, String(ts));
      setLastRedistributedAt(ts);
      setNow(ts);
    } catch (e) {
      setRedistributeErr((e as Error).message);
    } finally {
      setRedistributing(false);
    }
  }

  const types = useMemo(() => (counts ? orderedTypes(counts) : [...HONEYPOT_TYPES]), [counts]);
  const total = useMemo(() => types.reduce((sum, hp) => sum + (counts?.[hp] ?? 0), 0), [types, counts]);
  const pieData = useMemo(
    () => types.map((hp) => ({
      label: TYPE_LABELS[hp as keyof typeof TYPE_LABELS] ?? hp,
      value: counts?.[hp] ?? 0,
      fill: TYPE_COLORS[hp as keyof typeof TYPE_COLORS] ?? "#6b7a99"
    })),
    [types, counts]
  );
  const buttonLabel = redistributing ? "Redistributing…" : "Redistribute";

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Honeynet Demo</div>
            <div style={{ ...subtle, marginTop: 4 }}>
              How many honeypots of each type are running right now, with a manual override to re-run the ML model and redistribute them
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
            <button
              className="redistribute-btn"
              onClick={() => void handleRedistribute()}
              disabled={redistributing || onCooldown}
            >
              {buttonLabel}
            </button>
            {onCooldown && (
              <div style={{ fontSize: 11, color: "#f59e0b", fontFamily: "'Space Mono', monospace" }}>
                Cooldown: {formatCountdown(cooldownRemaining)} remaining
              </div>
            )}
          </div>
        </div>
        {redistributeErr && <div style={{ ...subtle, color: "#f87171", marginTop: 8 }}>{redistributeErr}</div>}
        <div style={{ ...subtle, marginTop: 8 }}>
          {lastRedistributedAt ? `Last redistributed ${timeAgo(lastRedistributedAt)}` : "Not redistributed yet this session"}
        </div>
      </div>

      <div style={twoCol}>

        {/* Left half — 6 honeypot type cells */}
        <div style={panel}>
          <div style={{ marginBottom: 14 }}>
            <div style={cardTitle}>Honeypot Types</div>
            <div style={{ ...subtle, marginTop: 4 }}>
              {counts === null
                ? (loadingState ? "Loading current honeypot counts…" : (stateErr || "No honeypot state available yet."))
                : `${total} honeypots running across ${types.length} type${types.length === 1 ? "" : "s"}`}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
            {types.map((hp) => (
              <CategoryCell
                key={hp}
                label={TYPE_LABELS[hp as keyof typeof TYPE_LABELS] ?? hp}
                value={counts?.[hp] ?? 0}
                accent={TYPE_COLORS[hp as keyof typeof TYPE_COLORS] ?? "#6b7a99"}
              />
            ))}
          </div>
        </div>

        {/* Right half  */}
        <div style={panel}>
          <div style={{ marginBottom: 14 }}>
            <div style={cardTitle}>Distribution</div>
            <div style={{ ...subtle, marginTop: 4 }}>Share of the honeynet held by each type</div>
          </div>
          <RaceBarChart data={pieData} height={240} />
          <div style={{ display: "grid", gap: 6, marginTop: 10 }}>
            {pieData.map((p) => {
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
        </div>
      </div>
    </div>
  );
}

function CategoryCell({ label, value, accent }: { label: string; value: number; accent: string }) {
  return (
    <div style={{
      position: "relative",
      overflow: "hidden",
      borderRadius: 10,
      border: "1px solid rgba(255,255,255,0.08)",
      background: "rgba(255,255,255,0.02)",
      padding: "14px 16px"
    }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,${accent},transparent)` }} />
      <div style={subtle}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 900, marginTop: 4, color: accent, lineHeight: 1 }}>{value}</div>
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
const twoCol: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(380px,1fr))", gap: 16 };
