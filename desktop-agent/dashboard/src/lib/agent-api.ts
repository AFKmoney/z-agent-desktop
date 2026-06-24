/**
 * Agent API client - configurable backend URL.
 *
 * In the sandbox/preview, requests go through Caddy with XTransformPort=8765.
 * In production (user's machine), point NEXT_PUBLIC_AGENT_API to the FastAPI URL.
 */
const AGENT_API_BASE =
  process.env.NEXT_PUBLIC_AGENT_API ||
  (typeof window !== "undefined" && window.location.hostname.includes("space-z.ai")
    ? ""  // Use relative paths through Caddy gateway
    : "http://localhost:8765");

const AGENT_PORT = "8765";

function buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
  const url = new URL(
    path.startsWith("http") ? path : `${AGENT_API_BASE}${path}`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost"
  );
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  // If using Caddy gateway (no explicit base), add XTransformPort
  if (!AGENT_API_BASE && typeof window !== "undefined") {
    url.searchParams.set("XTransformPort", AGENT_PORT);
  }
  return url.toString();
}

export async function agentFetch<T>(
  path: string,
  options?: RequestInit & { params?: Record<string, string | number | boolean> }
): Promise<T> {
  const { params, ...init } = options || {};
  const url = buildUrl(path, params);
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Agent API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function buildWsUrl(path: string): string {
  if (AGENT_API_BASE) {
    // Direct connection (user's machine)
    return AGENT_API_BASE.replace(/^http/, "ws") + path;
  }
  // Caddy gateway
  const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${typeof window !== "undefined" ? window.location.host : ""}${path}?XTransformPort=${AGENT_PORT}`;
}

// === Types ===

export interface AgentStatus {
  state: "idle" | "planning" | "executing" | "paused" | "error" | "stopped";
  current_task: {
    id: string;
    request: string;
    source: string;
    submitted_at: number;
    status: string;
  } | null;
  queue_size: number;
  memory: {
    facts_count: number;
    preferences_count: number;
    tasks_count: number;
    shortcuts_count: number;
    recent_tasks: Array<Record<string, unknown>>;
  } | null;
  uptime_s: number;
}

export interface TaskRecord {
  task_id: string;
  request: string;
  source?: string;
  plan?: {
    understanding: string;
    plan: Array<{
      step: number;
      action: string;
      params: Record<string, unknown>;
      reasoning: string;
    }>;
    metadata?: Record<string, unknown>;
  };
  result?: {
    total_steps: number;
    succeeded: number;
    failed: number;
    success: boolean;
    results: Array<Record<string, unknown>>;
  };
  success: boolean;
  timestamp: number;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  module?: string;
  line?: number;
}

export interface Screenshot {
  name: string;
  path: string;
  size: number;
  modified: number;
}

export interface ActionInfo {
  actions: string[];
}

// === API methods ===

export const agentApi = {
  health: () => agentFetch<{ status: string; timestamp: number }>("/api/health"),
  status: () => agentFetch<AgentStatus>("/api/status"),
  submitTask: (request: string, source = "dashboard") =>
    agentFetch<{ task_id: string; queued: boolean }>("/api/task", {
      method: "POST",
      body: JSON.stringify({ request, source }),
    }),
  recentTasks: (limit = 20) =>
    agentFetch<{ tasks: TaskRecord[] }>("/api/tasks/recent", { params: { limit } }),
  memory: () => agentFetch<Record<string, unknown>>("/api/memory"),
  command: (command: "start" | "stop" | "pause" | "resume") =>
    agentFetch<{ ok: boolean; state: string }>("/api/command", {
      method: "POST",
      body: JSON.stringify({ command }),
    }),
  actions: () => agentFetch<ActionInfo>("/api/actions"),
  screenshots: (limit = 20) =>
    agentFetch<{ screenshots: Screenshot[] }>("/api/screenshots", { params: { limit } }),
  captureScreenshot: () =>
    agentFetch<{ path: string; url: string }>("/api/screenshot/capture"),
  screenshotUrl: (filename: string) => buildUrl(`/api/screenshots/${filename}`),
  latestScreenshotUrl: () => buildUrl("/api/screenshot/latest"),
  perception: (question: string) =>
    agentFetch<Record<string, unknown>>("/api/perception/analyze", { params: { question } }),
};
