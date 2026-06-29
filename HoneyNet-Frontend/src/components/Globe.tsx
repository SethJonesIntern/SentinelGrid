import { useEffect, useRef } from "react";

interface Dot { lat: number; lon: number; }
interface Attack { srcLat: number; srcLon: number; dstLat: number; dstLon: number; progress: number; speed: number; color: string; }
interface Point { x: number; y: number; z: number; }

export default function Globe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

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

    // Random "attack" lines
    const attacks: Attack[] = [];
    const colors = ["#3b82f6", "#22d3ee", "#f87171", "#34d399", "#fbbf24"];
    for (let i = 0; i < 8; i++) {
      attacks.push({
        srcLat: (Math.random() - 0.5) * 140,
        srcLon: Math.random() * 360,
        dstLat: (Math.random() - 0.5) * 140,
        dstLon: Math.random() * 360,
        progress: Math.random(),
        speed: 0.003 + Math.random() * 0.004,
        color: colors[Math.floor(Math.random() * colors.length)]
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

    function draw() {
      ctx.clearRect(0, 0, W, H);

      // Globe sphere glow
      const grd = ctx.createRadialGradient(cx, cy, R * 0.3, cx, cy, R);
      grd.addColorStop(0, "rgba(29,78,216,0.06)");
      grd.addColorStop(0.7, "rgba(15,50,120,0.03)");
      grd.addColorStop(1, "rgba(59,130,246,0.08)");
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = grd;
      ctx.fill();

      // Outer ring
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(59,130,246,0.2)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Grid lines (latitude)
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

      // Grid lines (longitude)
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

      // Dots
      for (const dot of dots) {
        const p = project(dot.lat, dot.lon, angle);
        if (p.z < 0) continue;
        const brightness = (p.z / R) * 0.8 + 0.2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99,165,255,${brightness * 0.7})`;
        ctx.fill();
      }

      // Attack arcs
      for (const atk of attacks) {
        atk.progress += atk.speed;
        if (atk.progress > 1) atk.progress = 0;

        const src = project(atk.srcLat, atk.srcLon, angle);
        const dst = project(atk.dstLat, atk.dstLon, angle);

        if (src.z < 0 || dst.z < 0) continue;

        // Draw arc
        const t = atk.progress;
        const midX = (src.x + dst.x) / 2;
        const midY = (src.y + dst.y) / 2 - 60;

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.quadraticCurveTo(midX, midY, dst.x, dst.y);
        ctx.strokeStyle = `${atk.color}30`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Moving dot on arc
        const dotX = (1-t)*(1-t)*src.x + 2*(1-t)*t*midX + t*t*dst.x;
        const dotY = (1-t)*(1-t)*src.y + 2*(1-t)*t*midY + t*t*dst.y;
        ctx.beginPath();
        ctx.arc(dotX, dotY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = atk.color;
        ctx.fill();

        // Glow
        const glowGrd = ctx.createRadialGradient(dotX, dotY, 0, dotX, dotY, 8);
        glowGrd.addColorStop(0, atk.color + "80");
        glowGrd.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(dotX, dotY, 8, 0, Math.PI * 2);
        ctx.fillStyle = glowGrd;
        ctx.fill();
      }

      // Source dot highlights
      for (const atk of attacks) {
        const src = project(atk.srcLat, atk.srcLon, angle);
        if (src.z < 0) continue;
        ctx.beginPath();
        ctx.arc(src.x, src.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = "#f87171";
        ctx.fill();
      }

      angle += 0.08;
      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: "50%",
        right: "-80px",
        transform: "translateY(-50%)",
        width: "560px",
        height: "560px",
        opacity: 0.55,
        zIndex: 0,
        pointerEvents: "none"
      }}
    />
  );
}