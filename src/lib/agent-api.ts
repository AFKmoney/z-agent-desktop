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

  // Cost tracker
  costStats: (period: string = "all") =>
    agentFetch<Record<string, unknown>>("/api/costs/stats", { params: { period } }),
  costRecent: (limit = 50) =>
    agentFetch<{ records: unknown[] }>("/api/costs/recent", { params: { limit } }),

  // Audit log
  auditRecent: (params?: { limit?: number; filter_action?: string; only_blocked?: boolean; only_errors?: boolean }) =>
    agentFetch<{ entries: Array<Record<string, unknown>> }>("/api/audit/recent", { params: params || {} }),
  auditStats: () => agentFetch<Record<string, unknown>>("/api/audit/stats"),

  // Activity heatmap
  activityHeatmap: (days = 365) =>
    agentFetch<{ data: Array<Record<string, unknown>> }>("/api/activity/heatmap", { params: { days } }),
  activityStats: () => agentFetch<Record<string, unknown>>("/api/activity/stats"),

  // Scheduled tasks
  scheduledList: () => agentFetch<{ tasks: Array<Record<string, unknown>> }>("/api/scheduled"),
  scheduledCreate: (data: { name: string; request: string; schedule_type: string; schedule_expr: string }) =>
    agentFetch<Record<string, unknown>>("/api/scheduled", { method: "POST", body: JSON.stringify(data) }),
  scheduledUpdate: (id: string, data: Record<string, unknown>) =>
    agentFetch<Record<string, unknown>>(`/api/scheduled/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  scheduledDelete: (id: string) =>
    agentFetch<Record<string, unknown>>(`/api/scheduled/${id}`, { method: "DELETE" }),

  // Knowledge base
  kbStats: () => agentFetch<Record<string, unknown>>("/api/kb/stats"),
  kbDocuments: () => agentFetch<{ documents: Array<Record<string, unknown>>; count: number }>("/api/kb/documents"),
  kbSearch: (query: string, top_k = 5) =>
    agentFetch<Record<string, unknown>>("/api/kb/search", { method: "POST", body: JSON.stringify({ query, top_k }), params: {} }),
  kbDelete: (doc_id: string) =>
    agentFetch<Record<string, unknown>>(`/api/kb/documents/${doc_id}`, { method: "DELETE" }),

  // Notifications
  notifications: (limit = 50) =>
    agentFetch<{ notifications: Array<Record<string, unknown>> }>("/api/notifications", { params: { limit } }),

  // Multi-LLM Provider
  llmProviders: () => agentFetch<{ providers: Array<Record<string, unknown>> }>("/api/llm/providers"),
  llmTest: (provider: string) =>
    agentFetch<Record<string, unknown>>("/api/llm/test", { method: "POST", body: JSON.stringify({ provider }) }),
  llmSetPrimary: (provider: string) =>
    agentFetch<{ success: boolean; primary: string }>("/api/llm/set-primary", { method: "POST", body: JSON.stringify({ provider }) }),

  // Vector Memory
  vectorMemoryList: (memory_type?: string) =>
    agentFetch<{ memories: Array<Record<string, unknown>> }>("/api/vector-memory", { params: memory_type ? { memory_type } : {} }),
  vectorMemoryCreate: (data: { text: string; memory_type?: string; tags?: string[]; importance?: number }) =>
    agentFetch<Record<string, unknown>>("/api/vector-memory", { method: "POST", body: JSON.stringify(data) }),
  vectorMemorySearch: (query: string, top_k = 5) =>
    agentFetch<{ results: Array<Record<string, unknown>> }>("/api/vector-memory/search", { method: "POST", body: JSON.stringify({ query, top_k }) }),
  vectorMemoryStats: () => agentFetch<Record<string, unknown>>("/api/vector-memory/stats"),

  // Auto Skills
  autoSkillPatterns: (limit = 20) =>
    agentFetch<{ patterns: Array<Record<string, unknown>> }>("/api/auto-skills/patterns", { params: { limit } }),
  autoSkillStats: () => agentFetch<Record<string, unknown>>("/api/auto-skills/stats"),

  // Prompt Templates
  templatesList: (params?: { category?: string; search?: string }) =>
    agentFetch<{ templates: Array<Record<string, unknown>> }>("/api/templates", { params: params || {} }),
  templatesCreate: (data: { name: string; template: string; description?: string; category?: string; tags?: string[] }) =>
    agentFetch<Record<string, unknown>>("/api/templates", { method: "POST", body: JSON.stringify(data) }),
  templatesDelete: (id: string) =>
    agentFetch<Record<string, unknown>>(`/api/templates/${id}`, { method: "DELETE" }),

  // Webhooks
  webhooksList: () => agentFetch<{ webhooks: Array<Record<string, unknown>> }>("/api/webhooks"),
  webhooksCreate: (data: { name: string; template: string; auth_token?: string; sync?: boolean }) =>
    agentFetch<Record<string, unknown>>("/api/webhooks", { method: "POST", body: JSON.stringify(data) }),
  webhooksDelete: (id: string) =>
    agentFetch<Record<string, unknown>>(`/api/webhooks/${id}`, { method: "DELETE" }),

  // File Watcher
  watchRulesList: () => agentFetch<{ rules: Array<Record<string, unknown>> }>("/api/watch-rules"),
  watchRulesCreate: (data: { path: string; events: string[]; patterns: string[]; task_request: string; name?: string }) =>
    agentFetch<Record<string, unknown>>("/api/watch-rules", { method: "POST", body: JSON.stringify(data) }),
  watchRulesDelete: (id: string) =>
    agentFetch<Record<string, unknown>>(`/api/watch-rules/${id}`, { method: "DELETE" }),

  // Smart Suggestions
  suggestions: (current?: string, limit = 5) =>
    agentFetch<{ suggestions: Array<Record<string, unknown>> }>("/api/suggestions", { params: current ? { current, limit } : { limit } }),

  // Backup
  backupCreate: (include_screenshots = false) =>
    agentFetch<Record<string, unknown>>("/api/backup/create", { method: "POST", params: { include_screenshots } }),
  backupsList: () => agentFetch<{ backups: Array<Record<string, unknown>> }>("/api/backups"),
  backupsDelete: (name: string) =>
    agentFetch<Record<string, unknown>>(`/api/backups/${name}`, { method: "DELETE" }),
};
