import type { RawLogRow } from "./api";

export type CountPoint = {
  label: string;
  value: number;
};

export type SessionSummary = {
  session_id: string;
  src_ip: string;
  count: number;
  newest_id: number;
  newest_ts: string;
  oldest_ts: string;
  event_types: string[];
  commands: string[];
};

export function safeText(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "—";
}

export function formatTimestamp(ts?: string): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

export function timeAgo(ts?: string): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;

  const diffMs = Date.now() - d.getTime();
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

export function getCommandText(log: RawLogRow): string {
  const payload = log.raw_json?.payload ?? {};

  const candidates = [
    (payload as Record<string, unknown>).command,
    (payload as Record<string, unknown>).input,
    (payload as Record<string, unknown>).cmd,
    (payload as Record<string, unknown>).message,
    (payload as Record<string, unknown>).commands
  ];

  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (Array.isArray(value) && value.length > 0) {
      return value.map((v) => safeText(v)).join(", ");
    }
  }

  return "—";
}

export function groupBySession(logs: RawLogRow[]): SessionSummary[] {
  const map = new Map<string, RawLogRow[]>();

  for (const log of logs) {
    const sid = log.raw_json?.session_id ?? "unknown";
    if (!map.has(sid)) map.set(sid, []);
    map.get(sid)!.push(log);
  }

  const rows: SessionSummary[] = [];

  for (const [session_id, items] of map.entries()) {
    items.sort((a, b) => b.id - a.id);

    const newest = items[0];
    const oldest = items[items.length - 1];

    const event_types = Array.from(
      new Set(items.map((x) => x.raw_json?.event_type ?? "unknown"))
    );

    const commands = Array.from(
      new Set(
        items
          .map((x) => getCommandText(x))
          .filter((x) => x !== "—")
      )
    ).slice(0, 5);

    rows.push({
      session_id,
      src_ip: newest?.raw_json?.src_ip ?? "unknown",
      count: items.length,
      newest_id: newest?.id ?? 0,
      newest_ts: newest?.raw_json?.timestamp ?? "",
      oldest_ts: oldest?.raw_json?.timestamp ?? "",
      event_types,
      commands
    });
  }

  rows.sort((a, b) => b.newest_id - a.newest_id);
  return rows;
}

export function buildTopIps(logs: RawLogRow[], limit = 8): CountPoint[] {
  const counts = new Map<string, number>();

  for (const log of logs) {
    const ip = log.raw_json?.src_ip ?? "unknown";
    counts.set(ip, (counts.get(ip) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export function buildTopEventTypes(logs: RawLogRow[], limit = 8): CountPoint[] {
  const counts = new Map<string, number>();

  for (const log of logs) {
    const type = log.raw_json?.event_type ?? "unknown";
    counts.set(type, (counts.get(type) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export function buildTopCommands(logs: RawLogRow[], limit = 8): CountPoint[] {
  const counts = new Map<string, number>();

  for (const log of logs) {
    const cmd = getCommandText(log);
    if (cmd === "—") continue;
    counts.set(cmd, (counts.get(cmd) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export type HoneypotType = "SSH" | "HTTP" | "Redis" | "MySQL" | "FTP" | "SMTP" | "Other";

const TYPE_PATTERNS: { type: HoneypotType; patterns: RegExp[] }[] = [
  { type: "SSH", patterns: [/ssh/i, /cowrie/i, /telnet/i] },
  { type: "HTTP", patterns: [/http/i, /\bweb\b/i] },
  { type: "Redis", patterns: [/redis/i] },
  { type: "MySQL", patterns: [/mysql/i] },
  { type: "FTP", patterns: [/ftp/i] },
  { type: "SMTP", patterns: [/smtp/i] },
];

export function classifyHoneypotType(log: RawLogRow): HoneypotType {
  const raw = log.raw_json;
  const payload = raw?.payload as Record<string, unknown> | undefined;
  const protocolHint = payload?.protocol;

  const candidates = [
    raw?.sensor_id,
    typeof protocolHint === "string" ? protocolHint : undefined,
    raw?.event_type
  ];

  for (const candidate of candidates) {
    if (typeof candidate !== "string") continue;
    const match = TYPE_PATTERNS.find(({ patterns }) => patterns.some((p) => p.test(candidate)));
    if (match) return match.type;
  }

  return "Other";
}

export function buildHoneypotDistribution(logs: RawLogRow[]): CountPoint[] {
  const counts = new Map<HoneypotType, number>();

  for (const log of logs) {
    const type = classifyHoneypotType(log);
    if (type === "Other") continue;
    counts.set(type, (counts.get(type) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}

export function buildAttacksPerHour(logs: RawLogRow[]): CountPoint[] {
  const counts = new Map<string, number>();

  for (const log of logs) {
    const ts = log.raw_json?.timestamp;
    if (!ts) continue;
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) continue;

    const bucket = `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:00`;
    counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => {
      const aDate = new Date(`2026/${a.label.replace(" ", " ")}`);
      const bDate = new Date(`2026/${b.label.replace(" ", " ")}`);
      return aDate.getTime() - bDate.getTime();
    });
}