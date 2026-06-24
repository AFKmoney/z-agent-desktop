const AGENT_API_BASE = "";

function buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
  const url = new URL(path, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
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
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Agent API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function buildWsUrl(path: string): string {
  const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${typeof window !== "undefined" ? window.location.host : ""}${path}`;
}

export interface AgentStatus {
  state: string; current_task: unknown; queue_size: number; memory: unknown; uptime_s: number;
}
export interface TaskRecord { task_id: string; request: string; source?: string; plan?: unknown; result?: unknown; success: boolean; timestamp: number; }
export interface LogEntry { timestamp: string; level: string; logger: string; message: string; }
export interface Screenshot { name: string; path: string; size: number; modified: number; }
export interface ActionInfo { actions: string[]; }

export const agentApi = {
  health: () => agentFetch<{ status: string; timestamp: number }>("/api/health"),
  status: () => agentFetch<AgentStatus>("/api/status"),
  submitTask: (request: string, source = "dashboard") => agentFetch<{ task_id: string; queued: boolean }>("/api/task", { method: "POST", body: JSON.stringify({ request, source }) }),
  recentTasks: (limit = 20) => agentFetch<{ tasks: TaskRecord[] }>("/api/tasks/recent", { params: { limit } }),
  memory: () => agentFetch<Record<string, unknown>>("/api/memory"),
  command: (command: string) => agentFetch<{ ok: boolean; state: string }>("/api/command", { method: "POST", body: JSON.stringify({ command }) }),
  actions: () => agentFetch<ActionInfo>("/api/actions"),
  screenshots: (limit = 20) => agentFetch<{ screenshots: Screenshot[] }>("/api/screenshots", { params: { limit } }),
  captureScreenshot: () => agentFetch<{ path: string; url: string }>("/api/screenshot/capture"),
  screenshotUrl: (filename: string) => buildUrl(`/api/screenshots/${filename}`),
  perception: (question: string) => agentFetch<Record<string, unknown>>("/api/perception/analyze", { params: { question } }),

  // Cost tracker
  costStats: (period = "all") => agentFetch<Record<string, unknown>>("/api/costs/stats", { params: { period } }),
  costRecent: (limit = 50) => agentFetch<{ records: unknown[] }>("/api/costs/recent", { params: { limit } }),

  // Audit log
  auditRecent: (params?: Record<string, unknown>) => agentFetch<{ entries: Array<Record<string, unknown>> }>("/api/audit/recent", { params: params as Record<string, string | number | boolean> || {} }),
  auditStats: () => agentFetch<Record<string, unknown>>("/api/audit/stats"),

  // Activity
  activityHeatmap: (days = 365) => agentFetch<{ data: Array<Record<string, unknown>> }>("/api/activity/heatmap", { params: { days } }),
  activityStats: () => agentFetch<Record<string, unknown>>("/api/activity/stats"),

  // Scheduled tasks
  scheduledList: () => agentFetch<{ tasks: Array<Record<string, unknown>> }>("/api/scheduled"),
  scheduledCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/scheduled", { method: "POST", body: JSON.stringify(data) }),
  scheduledUpdate: (id: string, data: Record<string, unknown>) => agentFetch<Record<string, unknown>>(`/api/scheduled/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  scheduledDelete: (id: string) => agentFetch<Record<string, unknown>>(`/api/scheduled/${id}`, { method: "DELETE" }),

  // Knowledge base
  kbStats: () => agentFetch<Record<string, unknown>>("/api/kb/stats"),
  kbDocuments: () => agentFetch<{ documents: Array<Record<string, unknown>>; count: number }>("/api/kb/documents"),
  kbSearch: (query: string, top_k = 5) => agentFetch<Record<string, unknown>>("/api/kb/search", { method: "POST", body: JSON.stringify({ query, top_k }) }),
  kbDelete: (doc_id: string) => agentFetch<Record<string, unknown>>(`/api/kb/documents/${doc_id}`, { method: "DELETE" }),

  // Notifications
  notifications: (limit = 50) => agentFetch<{ notifications: Array<Record<string, unknown>> }>("/api/notifications", { params: { limit } }),

  // LLM providers
  llmProviders: () => agentFetch<{ providers: Array<Record<string, unknown>> }>("/api/llm/providers"),
  llmTest: (provider: string) => agentFetch<Record<string, unknown>>("/api/llm/test", { method: "POST", body: JSON.stringify({ provider }) }),
  llmSetPrimary: (provider: string) => agentFetch<{ success: boolean; primary: string }>("/api/llm/set-primary", { method: "POST", body: JSON.stringify({ provider }) }),

  // Vector memory
  vectorMemoryList: (memory_type?: string) => agentFetch<{ memories: Array<Record<string, unknown>> }>("/api/vector-memory", { params: memory_type ? { memory_type } : {} }),
  vectorMemoryCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/vector-memory", { method: "POST", body: JSON.stringify(data) }),
  vectorMemorySearch: (query: string, top_k = 5) => agentFetch<{ results: Array<Record<string, unknown>> }>("/api/vector-memory/search", { method: "POST", body: JSON.stringify({ query, top_k }) }),
  vectorMemoryStats: () => agentFetch<Record<string, unknown>>("/api/vector-memory/stats"),

  // Auto skills
  autoSkillPatterns: (limit = 20) => agentFetch<{ patterns: Array<Record<string, unknown>> }>("/api/auto-skills/patterns", { params: { limit } }),
  autoSkillStats: () => agentFetch<Record<string, unknown>>("/api/auto-skills/stats"),

  // Templates
  templatesList: (params?: Record<string, unknown>) => agentFetch<{ templates: Array<Record<string, unknown>> }>("/api/templates", { params: params as Record<string, string | number | boolean> || {} }),
  templatesCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/templates", { method: "POST", body: JSON.stringify(data) }),
  templatesDelete: (id: string) => agentFetch<Record<string, unknown>>(`/api/templates/${id}`, { method: "DELETE" }),

  // Webhooks
  webhooksList: () => agentFetch<{ webhooks: Array<Record<string, unknown>> }>("/api/webhooks"),
  webhooksCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/webhooks", { method: "POST", body: JSON.stringify(data) }),
  webhooksDelete: (id: string) => agentFetch<Record<string, unknown>>(`/api/webhooks/${id}`, { method: "DELETE" }),

  // File watcher
  watchRulesList: () => agentFetch<{ rules: Array<Record<string, unknown>> }>("/api/watch-rules"),
  watchRulesCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/watch-rules", { method: "POST", body: JSON.stringify(data) }),
  watchRulesDelete: (id: string) => agentFetch<Record<string, unknown>>(`/api/watch-rules/${id}`, { method: "DELETE" }),

  // Smart suggestions
  suggestions: (current?: string, limit = 5) => agentFetch<{ suggestions: Array<Record<string, unknown>> }>("/api/suggestions", { params: current ? { current, limit } : { limit } }),

  // Backup
  backupCreate: (include_screenshots = false) => agentFetch<Record<string, unknown>>("/api/backup/create", { method: "POST", params: { include_screenshots } }),
  backupsList: () => agentFetch<{ backups: Array<Record<string, unknown>> }>("/api/backups"),
  backupsDelete: (name: string) => agentFetch<Record<string, unknown>>(`/api/backups/${name}`, { method: "DELETE" }),

  // Environment variables
  envList: () => agentFetch<{ variables: Array<Record<string, unknown>>; categories: Array<Record<string, unknown>> }>("/api/env"),
  envStatus: () => agentFetch<Record<string, unknown>>("/api/env/status"),
  envSet: (key: string, value: string) => agentFetch<Record<string, unknown>>("/api/env", { method: "POST", body: JSON.stringify({ key, value }) }),
  envBatchSet: (updates: Record<string, string>) => agentFetch<Record<string, unknown>>("/api/env/batch", { method: "POST", body: JSON.stringify({ updates }) }),
  envDelete: (key: string) => agentFetch<Record<string, unknown>>(`/api/env/${key}`, { method: "DELETE" }),
  envTest: (key: string) => agentFetch<Record<string, unknown>>(`/api/env/test/${key}`, { method: "POST" }),

  // Chat
  chatList: () => agentFetch<{ conversations: Array<Record<string, unknown>> }>("/api/chat/conversations"),
  chatCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/chat/conversations", { method: "POST", body: JSON.stringify(data) }),
  chatGet: (convId: string) => agentFetch<Record<string, unknown>>(`/api/chat/conversations/${convId}`),
  chatDelete: (convId: string) => agentFetch<Record<string, unknown>>(`/api/chat/conversations/${convId}`, { method: "DELETE" }),
  chatUpdate: (convId: string, data: Record<string, unknown>) => agentFetch<Record<string, unknown>>(`/api/chat/conversations/${convId}`, { method: "PATCH", body: JSON.stringify(data) }),
  chatSend: (convId: string, message: string) => agentFetch<{ success: boolean; response: string; metadata?: Record<string, unknown> }>(`/api/chat/conversations/${convId}/send`, { method: "POST", body: JSON.stringify({ message }) }),
  chatSearch: (q: string) => agentFetch<{ results: Array<Record<string, unknown>> }>("/api/chat/search", { params: { q } }),
  chatStats: () => agentFetch<Record<string, unknown>>("/api/chat/stats"),

  // Custom agents
  agentsList: () => agentFetch<{ agents: Array<Record<string, unknown>> }>("/api/agents"),
  agentsCreate: (data: Record<string, unknown>) => agentFetch<Record<string, unknown>>("/api/agents", { method: "POST", body: JSON.stringify(data) }),
  agentsGet: (agentId: string) => agentFetch<Record<string, unknown>>(`/api/agents/${agentId}`),
  agentsUpdate: (agentId: string, data: Record<string, unknown>) => agentFetch<Record<string, unknown>>(`/api/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(data) }),
  agentsDelete: (agentId: string) => agentFetch<Record<string, unknown>>(`/api/agents/${agentId}`, { method: "DELETE" }),
  agentsStats: () => agentFetch<Record<string, unknown>>("/api/agents/stats"),
};
