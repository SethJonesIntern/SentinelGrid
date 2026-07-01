import { useEffect, useState } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import { api } from "../lib/api";
import type { GeoCoordsResponse } from "../lib/api";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

interface AttackMarker {
  ip: string;
  count: number;
  lat: number;
  lon: number;
  country: string;
  city: string;
}

interface TooltipState {
  x: number;
  y: number;
  marker: AttackMarker;
}

function circleRadius(count: number): number {
  return Math.min(3 + Math.sqrt(count) * 2.5, 30);
}

function circleColor(count: number): string {
  if (count >= 100) return "#f87171";
  if (count >= 20) return "#fb923c";
  if (count >= 5) return "#fbbf24";
  return "#34d399";
}

export default function LocationPage() {
  const [markers, setMarkers] = useState<AttackMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<{ done: number; total: number } | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setMarkers([]);
    setResolving(null);
    try {
      const resp = await api.logs(2000);

      // Count attacks per unique IP
      const ipCounts = new Map<string, number>();
      for (const row of resp.logs) {
        const ip = row.raw_json?.src_ip;
        if (!ip) continue;
        ipCounts.set(ip, (ipCounts.get(ip) ?? 0) + 1);
      }

      const uniqueIps = Array.from(ipCounts.keys());
      setResolving({ done: 0, total: uniqueIps.length });

      // Resolve coordinates for each unique IP via /get_coords.
      // Promise.allSettled so private/reserved IPs (404) are silently skipped.
      let done = 0;
      const results = await Promise.allSettled(
        uniqueIps.map((ip) =>
          api.geo.coords(ip).then((r: GeoCoordsResponse) => {
            setResolving({ done: ++done, total: uniqueIps.length });
            return r;
          })
        )
      );

      const resolved: AttackMarker[] = [];
      for (let i = 0; i < uniqueIps.length; i++) {
        const r = results[i];
        if (r.status === "rejected") continue;
        const { latitude, longitude, city, country } = r.value;
        resolved.push({
          ip: uniqueIps[i],
          count: ipCounts.get(uniqueIps[i]) ?? 0,
          lat: latitude,
          lon: longitude,
          city: city ?? "",
          country: country ?? "Unknown",
        });
      }

      setMarkers(resolved.sort((a, b) => b.count - a.count));
    } finally {
      setLoading(false);
      setResolving(null);
    }
  }

  const totalAttacks = markers.reduce((s, m) => s + m.count, 0);
  const uniqueCountries = new Set(markers.map(m => m.country)).size;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 900, letterSpacing: "0.08em", color: "#e2e8f4" }}>
            ATTACK ORIGIN MAP
          </h1>
          <div style={{ fontSize: 12, color: "#4b6080", marginTop: 4, fontFamily: "'Space Mono', monospace" }}>
            Geographic distribution of threat actors
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          {[
            { label: "Mapped IPs", value: markers.length },
            { label: "Total Attacks", value: totalAttacks },
            { label: "Countries", value: uniqueCountries }
          ].map(({ label, value }) => (
            <div key={label} style={{
              padding: "10px 18px",
              background: "rgba(6,10,24,0.7)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 10,
              textAlign: "center"
            }}>
              <div style={{ fontSize: 20, fontWeight: 900, color: "#e2e8f4" }}>{value}</div>
              <div style={{ fontSize: 10, color: "#4b6080", letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "'Space Mono', monospace" }}>
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Map + Sidebar */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        {/* World Map */}
        <div style={{
          flex: 1,
          background: "rgba(6,10,24,0.85)",
          border: "1px solid rgba(59,130,246,0.15)",
          borderRadius: 16,
          overflow: "hidden",
          position: "relative"
        }}>
          <ComposableMap
            projectionConfig={{ scale: 160, center: [0, 10] }}
            style={{ width: "100%", height: "auto", display: "block" }}
            width={900}
            height={440}
          >
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    style={{
                      default: { fill: "#0d1630", stroke: "#1e2d50", strokeWidth: 0.5, outline: "none" },
                      hover:   { fill: "#0d1630", stroke: "#1e2d50", strokeWidth: 0.5, outline: "none" },
                      pressed: { fill: "#0d1630", stroke: "#1e2d50", strokeWidth: 0.5, outline: "none" }
                    }}
                  />
                ))
              }
            </Geographies>

            {[...markers]
              .sort((a, b) => b.count - a.count)
              .map((m) => (
                <Marker key={m.ip} coordinates={[m.lon, m.lat]}>
                  <circle
                    r={circleRadius(m.count)}
                    fill={circleColor(m.count)}
                    fillOpacity={0.55}
                    stroke={circleColor(m.count)}
                    strokeWidth={1}
                    strokeOpacity={0.9}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={(e) => {
                      const svg = e.currentTarget.ownerSVGElement;
                      if (!svg) return;
                      const rect = svg.getBoundingClientRect();
                      setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, marker: m });
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                </Marker>
              ))}
          </ComposableMap>

          {/* Tooltip */}
          {tooltip && (
            <div style={{
              position: "absolute",
              left: tooltip.x + 14,
              top: tooltip.y - 8,
              background: "rgba(6,10,24,0.96)",
              border: "1px solid rgba(59,130,246,0.35)",
              borderRadius: 8,
              padding: "8px 12px",
              fontSize: 12,
              pointerEvents: "none",
              zIndex: 10,
              whiteSpace: "nowrap",
              boxShadow: "0 4px 20px rgba(0,0,0,0.5)"
            }}>
              <div style={{ color: "#e2e8f4", fontWeight: 700, fontFamily: "'Space Mono', monospace" }}>
                {tooltip.marker.ip}
              </div>
              <div style={{ color: "#8896b0", marginTop: 2 }}>
                {[tooltip.marker.city, tooltip.marker.country].filter(Boolean).join(", ")}
              </div>
              <div style={{ color: circleColor(tooltip.marker.count), marginTop: 4, fontWeight: 700 }}>
                {tooltip.marker.count} attacks
              </div>
            </div>
          )}

          {loading && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(2,5,16,0.6)",
              color: "#4b6080",
              fontSize: 13,
              fontFamily: "'Space Mono', monospace",
              letterSpacing: "0.06em"
            }}>
              {resolving
                ? `RESOLVING IPs… ${resolving.done}/${resolving.total}`
                : "LOADING THREAT DATA..."}
            </div>
          )}

        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, width: 220, flexShrink: 0 }}>
          {/* Legend */}
          <div style={{
            background: "rgba(6,10,24,0.85)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 12,
            padding: "14px 16px"
          }}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
              color: "#3d5278", marginBottom: 14,
              fontFamily: "'Space Mono', monospace", textTransform: "uppercase"
            }}>
              Attack Intensity
            </div>
            {[
              { label: "1–4 attacks",   color: "#34d399" },
              { label: "5–19 attacks",  color: "#fbbf24" },
              { label: "20–99 attacks", color: "#fb923c" },
              { label: "100+ attacks",  color: "#f87171" }
            ].map(({ label, color }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <svg width={20} height={20} style={{ flexShrink: 0 }}>
                  <circle cx={10} cy={10} r={8} fill={color} fillOpacity={0.55} stroke={color} strokeWidth={1} />
                </svg>
                <span style={{ fontSize: 11, color: "#8896b0" }}>{label}</span>
              </div>
            ))}
          </div>

          {/* Top Attackers */}
          <div style={{
            background: "rgba(6,10,24,0.85)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 12,
            padding: "14px 16px",
            maxHeight: 380,
            overflowY: "auto"
          }}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
              color: "#3d5278", marginBottom: 14,
              fontFamily: "'Space Mono', monospace", textTransform: "uppercase"
            }}>
              Top Attackers
            </div>
            {markers.length === 0 && !loading && (
              <div style={{ color: "#3d5278", fontSize: 11, fontFamily: "'Space Mono', monospace" }}>
                No data yet
              </div>
            )}
            {markers.slice(0, 15).map((m, i) => (
              <div key={m.ip} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: 11, color: "#8896b0", fontFamily: "'Space Mono', monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 120 }}>
                    <span style={{ color: "#3d5278", marginRight: 5 }}>#{i + 1}</span>
                    {m.ip}
                  </div>
                  <span style={{ fontSize: 11, color: circleColor(m.count), fontWeight: 700, flexShrink: 0, marginLeft: 4 }}>
                    {m.count}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: "#3d5278", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {m.country}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
