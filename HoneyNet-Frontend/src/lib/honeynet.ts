//have to wait on API to return the amount of different honeypot types 

export const HONEYPOT_TYPES = ["ssh", "http", "redis", "mysql", "ftp", "smtp"] as const;
export type HoneypotType = typeof HONEYPOT_TYPES[number];

export const TYPE_LABELS: Record<HoneypotType, string> = {
  ssh: "SSH",
  http: "HTTP",
  redis: "Redis",
  mysql: "MySQL",
  ftp: "FTP",
  smtp: "SMTP"
};

export const TYPE_COLORS: Record<HoneypotType, string> = {
  ssh: "#3b82f6",
  http: "#22d3ee",
  redis: "#f87171",
  mysql: "#f59e0b",
  ftp: "#a78bfa",
  smtp: "#34d399"
};
