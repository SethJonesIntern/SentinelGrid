import React, { useEffect, useMemo, useState } from "react";
import { api, API_URL } from "../lib/api";
import { HONEYPOT_TYPES, TYPE_COLORS, TYPE_LABELS } from "../lib/honeynet";
import RaceBarChart from "../components/RaceBarChart";

const COOLDOWN_MS = 10 * 60 * 1000;
const LAST_REDISTRIBUTED_KEY = "sg_redistribute_last_at";

// distributable pool = total (12) minus base (6 always-on)
const DISTRIBUTABLE = 6;
// FTP cannot scale — its distributable count is always 0
const SCALABLE_TYPES = HONEYPOT_TYPES.filter((hp) => hp !== "ftp");

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

type HistoryEntry = {
  counts: Record<string, number>;
  recorded_at: string;
};

export default function DemoPage() {
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [loadingState, setLoadingState] = useState(true);
  const [stateErr, setStateErr] = useState("");
  const [lastRedistributedAt, setLastRedistributedAt] = useState<number | null>(() => {
    const stored = localStorage.getItem(LAST_REDISTRIBUTED_KEY);
    return stored ? Number(stored) : null;
  });
  const [now, setNow] = useState(() => Date.now());

  //manual set panel 
  const[showManual, setShowManual] = useState(false);
  const[manualCounts, setManualCounts] = useState<Record<string, number>>(
    () => Object.fromEntries(SCALABLE_TYPES.map((hp) => [hp, 0]))
  );
  const [manualErr, setManualErr] = useState("");
  const [submittingManual, setSubmittingManual] = useState(false);
  const manualTotal= SCALABLE_TYPES.reduce((s, hp) => s + (manualCounts[hp] ?? 0), 0);
  const manualValid= manualTotal === DISTRIBUTABLE;

  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    function fetchHistory() {
      fetch(`${API_URL}/distribution/history`)
        .then((r) => r.json())
        .then((j) => {
          const entries: HistoryEntry[] = Array.isArray(j?.history) ? j.history : [];
          setHistory(entries.slice(-5).reverse());
        })
        .catch(() => {});
    }
    fetchHistory();
    const id = window.setInterval(fetchHistory, 30_000);
    return () => window.clearInterval(id);
  }, []);

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

  async function handleSetManual() {
    if (!manualValid || submittingManual) return;
    setSubmittingManual(true);
    setManualErr("");
    try {
      const token = localStorage.getItem("sg_auth_token");
      if (!token) { setManualErr("Not logged in"); return; }
      const payload: Record<string, number> = { ftp: 0 };
      for (const hp of SCALABLE_TYPES) payload[hp] = manualCounts[hp] ?? 0;
      await api.ml.setDistributionCounts(payload, token);
      await loadState();
      const ts = Date.now();
      localStorage.setItem(LAST_REDISTRIBUTED_KEY, String(ts));
      setLastRedistributedAt(ts);
      setNow(ts);
      setShowManual(false);
      setTimeout(() => void loadState(), 10000);
    } catch (e) {
      setManualErr((e as Error).message);
    } finally {
      setSubmittingManual(false);
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

  return (
    <div style={{ display: "grid", gap: 16 }}>

      {/* Header */}
      <div style={panel}>
        <div style={topRow}>
          <div>
            <div style={pageTitle}>Honeypot Distribution</div>
            <div style={{ ...subtle, marginTop: 4 }}>
              Current count of running honeypots by type  
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="redistribute-btn"
                onClick={() => { setShowManual((v) => !v); setManualErr(""); }}
                style={{ opacity: showManual ? 0.6 : 1 }}
              >
                {showManual ? "Cancel" : "Set Manual Distribution"}
              </button>
            </div>
            {onCooldown && (
              <div style={{ fontSize: 11, color: "#f59e0b", fontFamily: "'Space Mono', monospace" }}>
                Cooldown: {formatCountdown(cooldownRemaining)} remaining
              </div>
            )}
          </div>
        </div>
        <div style={{ ...subtle, marginTop: 8 }}>
          {lastRedistributedAt ? `Last redistributed ${timeAgo(lastRedistributedAt)}` : "Not redistributed yet this session"}
        </div>

        {/* Manual set panel */}
        {showManual && (
          <div style={{ marginTop: 20, borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 18 }}>
            <div style={{ ...cardTitle, marginBottom: 4 }}>Set Honeypot Counts Manually</div>
            <div style={{ ...subtle, marginBottom: 14 }}>
              Distribute {DISTRIBUTABLE} slots across types (each type  gets a default of at least 1 deployed) with a total of 12 honeypots.
               FTP is fixed at 1 and cannot scale.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 14 }}>
              {SCALABLE_TYPES.map((hp) => {
                const color = TYPE_COLORS[hp as keyof typeof TYPE_COLORS] ?? "#6b7a99";
                const remaining = DISTRIBUTABLE - manualTotal;
                return (
                  <div key={hp} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <label style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color, fontFamily: "'Space Mono', monospace" }}>
                      {TYPE_LABELS[hp as keyof typeof TYPE_LABELS] ?? hp}
                    </label>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <button
                        type="button"
                        onClick={() => setManualCounts((c) => ({ ...c, [hp]: Math.max(0, (c[hp] ?? 0) - 1) }))}
                        disabled={(manualCounts[hp] ?? 0) === 0}
                        style={{ ...stepBtn, opacity: (manualCounts[hp] ?? 0) === 0 ? 0.3 : 1 }}
                      >−</button>
                      <input
                        type="number"
                        min={0}
                        max={(manualCounts[hp] ?? 0) + remaining}
                        value={manualCounts[hp] ?? 0}
                        onChange={(e) => {
                          const v = Math.max(0, Math.min(Number(e.target.value), (manualCounts[hp] ?? 0) + remaining));
                          setManualCounts((c) => ({ ...c, [hp]: v }));
                        }}
                        style={{ ...numInput, borderColor: color + "55" }}
                      />
                      <button
                        type="button"
                        onClick={() => setManualCounts((c) => ({ ...c, [hp]: (c[hp] ?? 0) + 1 }))}
                        disabled={remaining === 0}
                        style={{ ...stepBtn, opacity: remaining === 0 ? 0.3 : 1 }}
                      >+</button>
                    </div>
                    <div style={{ fontSize: 10, color: "#4b5f7c", fontFamily: "'Space Mono', monospace" }}>
                      total: {(manualCounts[hp] ?? 0) + 1} 
                    </div>
                  </div>
                );
              })}
              {/* FTP locked */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#6b7a99", fontFamily: "'Space Mono', monospace" }}>
                  FTP <span style={{ color: "#4b5f7c" }}>(fixed)</span>
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button type="button" disabled style={{ ...stepBtn, opacity: 0.2 }}>−</button>
                  <input type="number" value={1} readOnly style={{ ...numInput, opacity: 0.4, cursor: "not-allowed" }} />
                  <button type="button" disabled style={{ ...stepBtn, opacity: 0.2 }}>+</button>
                </div>
                <div style={{ fontSize: 10, color: "#4b5f7c", fontFamily: "'Space Mono', monospace" }}>total: 1</div>
              </div>
            </div>

            {/* Total indicator */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: manualValid ? "#34d399" : "#f59e0b", fontFamily: "'Space Mono', monospace", fontWeight: 700 }}>
                Distributable used: {manualTotal} / {DISTRIBUTABLE}
                {manualValid ? "  ✓" : `  (${DISTRIBUTABLE - manualTotal} remaining)`}
              </div>
              <div style={{ fontSize: 12, color: "#4b5f7c" }}>
                → total honeynet: {manualTotal + HONEYPOT_TYPES.length} 
              </div>
            </div>

            {manualErr && <div style={{ ...subtle, color: "#f87171", marginBottom: 10 }}>{manualErr}</div>}

            <button
              onClick={() => void handleSetManual()}
              disabled={!manualValid || submittingManual}
              style={{ ...applyBtn, opacity: !manualValid || submittingManual ? 0.4 : 1 }}
            >
              {submittingManual ? "Applying…" : "Apply Distribution"}
            </button>
          </div>
        )}
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
              return (
                <div key={p.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: p.fill, flexShrink: 0 }} />
                  <span style={{ color: "#8896b0", flex: 1, fontFamily: "'Space Mono',monospace" }}>{p.label}</span>
                  <span style={{ color: p.fill, fontWeight: 700, minWidth: 24, textAlign: "right" }}>{p.value}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Distribution History */}
      {history.length > 0 && (
        <div style={panel}>
          <div style={{ marginBottom: 16 }}>
            <div style={cardTitle}>Distribution History</div>
            <div style={{ ...subtle, marginTop: 4 }}>Last {history.length} unique distributions </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
            {history.map((entry, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <RadarChart counts={entry.counts} size={280} />
                <div style={{ fontSize: 10, color: "#4b5f7c", fontFamily: "'Space Mono',monospace", textAlign: "center" }}>
                  {(() => {
                    const raw = entry.recorded_at;
                    const normalized = /[Zz]$|[+-]\d{2}:\d{2}$/.test(raw) ? raw : raw.replace(" ", "T") + "Z";
                    const d = new Date(normalized);
                    return isNaN(d.getTime()) ? raw : d.toLocaleString();
                  })()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const RADAR_AXES = ["ssh", "http", "mysql", "redis", "ftp", "smtp"] as const;
const FLEXIBLE_SLOTS = 6;
const BASELINE = 1;
const MAX_VALUE = FLEXIBLE_SLOTS + BASELINE; // max per service = 7
const RINGS = [2, 4, 6];

function allocateCounts(counts: Record<string, number>): Record<string, number> {
  // API now returns literal per-type counts (already summing to 12) — use them as-is.
  return Object.fromEntries(RADAR_AXES.map((key) => [key, counts[key] ?? counts[`${key}_honeypot`] ?? 0]));
}

function RadarChart({ counts: rawCounts, size }: { counts: Record<string, number>; size: number }) {
  const cx = size / 2;
  const cy = size / 2;
  const R = size * 0.38;
  const n = RADAR_AXES.length;

  function axisPoint(i: number, r: number): [number, number] {
    const angle = (Math.PI / 2) - (2 * Math.PI * i) / n;
    return [cx + r * Math.cos(angle), cy - r * Math.sin(angle)];
  }

  // Ring polygons
  const ringPaths = RINGS.map((ring) => {
    const pts = RADAR_AXES.map((_, i) => {
      const r = (ring / MAX_VALUE) * R;
      return axisPoint(i, r).join(",");
    });
    return pts.join(" ");
  });

  // Data polygon — counts come straight from the API and already sum to 12
  const counts = allocateCounts(rawCounts);
  const dataPoints = RADAR_AXES.map((key, i) => {
    const count = counts[key];
    const r = Math.min((count / MAX_VALUE) * R, R);
    return axisPoint(i, r);
  });
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";

  const labelCounts = RADAR_AXES.map((key) => counts[key]);

  return (
    <svg width={size} height={size} style={{ overflow: "visible" }}>
      {/* Ring grid */}
      {ringPaths.map((pts, ri) => (
        <polygon key={ri} points={pts} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
      ))}
      {/* Ring labels */}
      {RINGS.map((ring) => {
        const [lx, ly] = axisPoint(0, (ring / MAX_VALUE) * R);
        return (
          <text key={ring} x={lx + 4} y={ly} fill="rgba(255,255,255,0.2)" fontSize={8} fontFamily="'Space Mono',monospace">{ring}</text>
        );
      })}
      {/* Axis spokes */}
      {RADAR_AXES.map((_, i) => {
        const [ex, ey] = axisPoint(i, R);
        return <line key={i} x1={cx} y1={cy} x2={ex} y2={ey} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />;
      })}
      {/* Data fill */}
      <path d={dataPath} fill="rgba(18,224,216,0.18)" stroke="#12e0d8" strokeWidth={1.5} />
      {/* Data dots */}
      {dataPoints.map(([px, py], i) => (
        <circle key={i} cx={px} cy={py} r={3} fill="#12e0d8" />
      ))}
      {/* Axis labels */}
      {RADAR_AXES.map((key, i) => {
        const [lx, ly] = axisPoint(i, R + 20);
        const color = TYPE_COLORS[key as keyof typeof TYPE_COLORS] ?? "#8896b0";
        const label = TYPE_LABELS[key as keyof typeof TYPE_LABELS] ?? key;
        return (
          <g key={key}>
            <text x={lx} y={ly - 2} textAnchor="middle" fill={color} fontSize={9} fontWeight={700} fontFamily="'Space Mono',monospace">{label}</text>
            <text x={lx} y={ly + 9} textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize={8} fontFamily="'Space Mono',monospace">{labelCounts[i]}</text>
          </g>
        );
      })}
    </svg>
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

const stepBtn: React.CSSProperties = {
  width: 28, height: 28, borderRadius: 6,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(255,255,255,0.05)",
  color: "#c8d3e8", fontSize: 16, cursor: "pointer",
  display: "flex", alignItems: "center", justifyContent: "center",
  flexShrink: 0, fontFamily: "inherit",
};

const numInput: React.CSSProperties = {
  width: 54, textAlign: "center",
  padding: "5px 8px", borderRadius: 7,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(255,255,255,0.04)",
  color: "#e2e8f4", fontSize: 14, fontWeight: 700,
  fontFamily: "'Space Mono', monospace",
  outline: "none", colorScheme: "dark",
};

const applyBtn: React.CSSProperties = {
  padding: "9px 20px", borderRadius: 9,
  border: "1px solid rgba(52,211,153,0.4)",
  background: "rgba(52,211,153,0.12)",
  color: "#34d399", fontWeight: 700, fontSize: 13,
  cursor: "pointer", fontFamily: "inherit",
};
