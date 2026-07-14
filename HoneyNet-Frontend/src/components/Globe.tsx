import { useEffect, useRef, useState } from "react";

interface Dot { lat: number; lon: number; }
interface Attack {
  srcLat: number;
  srcLon: number;
  dstLat: number;
  dstLon: number;
  progress: number;
  speed: number;
  color: string;
  srcIp: string;
  srcCity: string;
  srcCountry: string;
}
interface Point { x: number; y: number; z: number; }
interface HoverPoint {
  x: number;
  y: number;
  ip: string;
  city: string;
  country: string;
}
interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  ip: string;
  city: string;
  country: string;
}

export default function Globe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const hoverPointsRef = useRef<HoverPoint[]>([]);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    ip: "",
    city: "",
    country: "",
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d") as CanvasRenderingContext2D;
    if (!ctx) return;

    const W = 560;
    const H = 560;
    canvas.width = W;
    canvas.height = H;
    const cx = W / 2;
    const cy = H / 2;
    const R = 220;

    let angle = 0;

    // Dot grid for globe
    const dots: Dot[] = [];
    for (let lat = -80; lat <= 80; lat += 12) {
      const latRad = (lat * Math.PI) / 180;
      const circumference = Math.cos(latRad);
      const numDots = Math.max(4, Math.round(circumference * 28));
      for (let i = 0; i < numDots; i++) {
        dots.push({ lat, lon: (i / numDots) * 360 });
      }
    }

    // Sample attacker sources so hover can display IP + location.
    const sources = [
      { ip: "103.219.44.12", city: "Hanoi", country: "VN", lat: 21.03, lon: 105.85 },
      { ip: "45.146.164.87", city: "Bucharest", country: "RO", lat: 44.43, lon: 26.1 },
      { ip: "193.32.162.55", city: "Moscow", country: "RU", lat: 55.75, lon: 37.62 },
      { ip: "185.220.101.7", city: "Frankfurt", country: "DE", lat: 50.11, lon: 8.68 },
      { ip: "23.129.64.184", city: "Sao Paulo", country: "BR", lat: -23.55, lon: -46.63 },
      { ip: "139.99.238.14", city: "Singapore", country: "SG", lat: 1.35, lon: 103.82 },
      { ip: "92.63.197.153", city: "Amsterdam", country: "NL", lat: 52.37, lon: 4.9 },
      { ip: "161.35.70.249", city: "Bangalore", country: "IN", lat: 12.97, lon: 77.59 },
    ];

    // Random "attack" lines
    const attacks: Attack[] = [];
    const colors = ["#3b82f6", "#22d3ee", "#f87171", "#34d399", "#fbbf24"];
    for (let i = 0; i < 8; i++) {
      const src = sources[Math.floor(Math.random() * sources.length)];
      attacks.push({
        srcLat: src.lat,
        srcLon: src.lon,
        dstLat: (Math.random() - 0.5) * 140,
        dstLon: Math.random() * 360,
        progress: Math.random(),
        speed: 0.003 + Math.random() * 0.004,
        color: colors[Math.floor(Math.random() * colors.length)],
        srcIp: src.ip,
        srcCity: src.city,
        srcCountry: src.country,
      });
    }

    function project(lat: number, lon: number, rotY: number): Point {
      const latR = (lat * Math.PI) / 180;
      const lonR = ((lon + rotY) * Math.PI) / 180;
      const x = R * Math.cos(latR) * Math.sin(lonR);
      const y = -R * Math.sin(latR);
      const z = R * Math.cos(latR) * Math.cos(lonR);
      return { x: cx + x, y: cy + y, z };
    }
    function draw(){
      ctx.clearRect(0, 0, W, H);

      //globe sphere glow
      const grd = ctx.createRadialGradient(cx, cy, R * 0.3, cx, cy, R);
      grd.addColorStop(0, "rgba(29,78,216,0.06)");
      grd.addColorStop(0.7, "rgba(15,50,120,0.03)");
      grd.addColorStop(1, "rgba(59,130,246,0.08)");
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = grd;
      ctx.fill();

      //outer ring
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(59,130,246,0.2)";
      ctx.lineWidth = 1;
      ctx.stroke();

      //grid lines (latitude)
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        let first = true;
        for (let lon = 0; lon <= 360; lon += 4) {
          const p = project(lat, lon, angle);
          if (p.z > 0) {
            if (first) { ctx.moveTo(p.x, p.y); first = false; }
            else ctx.lineTo(p.x, p.y);
          } else {
            first = true;
          }
        }
        ctx.strokeStyle = "rgba(59,130,246,0.08)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      // longitude
      for (let lon = 0; lon < 360; lon += 30) {
        ctx.beginPath();
        let first = true;
        for (let lat = -80; lat <= 80; lat += 4) {
          const p = project(lat, lon, angle);
          if (p.z > 0) {
            if (first) { ctx.moveTo(p.x, p.y); first = false; }
            else ctx.lineTo(p.x, p.y);
          } else {
            first = true;
          }
        }
        ctx.strokeStyle = "rgba(59,130,246,0.08)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      //dots
      for (const dot of dots) {
        const p = project(dot.lat, dot.lon, angle);
        if (p.z < 0) continue;
        const brightness = (p.z / R) * 0.8 + 0.2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99,165,255,${brightness * 0.7})`;
        ctx.fill();
      }

      //attack arcs
      for (const atk of attacks) {
        atk.progress += atk.speed;
        if (atk.progress > 1) atk.progress = 0;

        const src = project(atk.srcLat, atk.srcLon, angle);
        const dst = project(atk.dstLat, atk.dstLon, angle);

        if (src.z < 0 || dst.z < 0) continue;

        //draw arc
        const t = atk.progress;
        const midX = (src.x + dst.x) / 2;
        const midY = (src.y + dst.y) / 2 - 60;

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.quadraticCurveTo(midX, midY, dst.x, dst.y);
        ctx.strokeStyle = `${atk.color}30`;
        ctx.lineWidth = 1;
        ctx.stroke();
        const dotX = (1-t)*(1-t)*src.x + 2*(1-t)*t*midX + t*t*dst.x;
        const dotY = (1-t)*(1-t)*src.y + 2*(1-t)*t*midY + t*t*dst.y;
        ctx.beginPath();
        ctx.arc(dotX, dotY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = atk.color;
        ctx.fill();

        const glowGrd = ctx.createRadialGradient(dotX, dotY, 0, dotX, dotY, 8);
        glowGrd.addColorStop(0, atk.color + "80");
        glowGrd.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(dotX, dotY, 8, 0, Math.PI * 2);
        ctx.fillStyle = glowGrd;
        ctx.fill();
      }

      // source dot highlights and hover points
      const hoverPoints: HoverPoint[] = [];
      for (const atk of attacks) {
        const src = project(atk.srcLat, atk.srcLon, angle);
        if (src.z < 0) continue;
        ctx.beginPath();
        ctx.arc(src.x, src.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = "#f87171";
        ctx.fill();

        hoverPoints.push({
          x: src.x,
          y: src.y,
          ip: atk.srcIp,
          city: atk.srcCity,
          country: atk.srcCountry,
        });
      }

      hoverPointsRef.current = hoverPoints;

      angle += 0.08;
      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const sx = canvas.width / rect.width;
    const sy = canvas.height / rect.height;
    const mx = (e.clientX - rect.left) * sx;
    const my = (e.clientY - rect.top) * sy;

    let nearest: HoverPoint | null = null;
    let nearestDist = 14;

    for (const p of hoverPointsRef.current) {
      const dx = p.x - mx;
      const dy = p.y - my;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < nearestDist) {
        nearest = p;
        nearestDist = d;
      }
    }

    if (!nearest) {
      if (tooltip.visible) setTooltip((t) => ({ ...t, visible: false }));
      return;
    }

    setTooltip({
      visible: true,
      x: e.clientX - rect.left + 10,
      y: e.clientY - rect.top - 8,
      ip: nearest.ip,
      city: nearest.city,
      country: nearest.country,
    });
  }

  return (
    <div
      style={{
        position: "fixed",
        top: "50%",
        right: "-80px",
        transform: "translateY(-50%)",
        width: "560px",
        height: "560px",
        opacity: 0.55,
        zIndex: 0,
      }}
    >
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
        style={{
          width: "560px",
          height: "560px",
          pointerEvents: "auto",
        }}
      />
      {tooltip.visible && (
        <div
          style={{
            position: "absolute",
            left: tooltip.x,
            top: tooltip.y,
            background: "rgba(6,10,24,0.92)",
            border: "1px solid rgba(99,165,255,0.35)",
            borderRadius: 8,
            padding: "6px 10px",
            color: "#dbeafe",
            fontSize: 11,
            fontFamily: "'Space Mono', monospace",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            boxShadow: "0 6px 18px rgba(0,0,0,0.35)",
          }}
        >
          <div style={{ fontWeight: 700 }}>{tooltip.ip}</div>
          <div style={{ color: "#93c5fd", marginTop: 2 }}>{tooltip.city}, {tooltip.country}</div>
        </div>
      )}
    </div>
  );
}