"use client";

import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  DollarSign, Activity, Shield, Clock, BookOpen, Bell,
  TrendingUp, Calendar, Trash2, Plus, Search, AlertCircle,
  CheckCircle2, XCircle, Ban, FileText,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { AnimatedCounter } from "./index";

// ============ Activity Heatmap (GitHub-style) ============
export function ActivityHeatmap() {
  const [data, setData] = useState<Array<Record<string, unknown>>>([]);
  const [stats, setStats] = useState<Record<string, unknown>>({});

  useEffect(() => {
    const load = async () => {
      try {
        const [h, s] = await Promise.all([
          agentApi.activityHeatmap(91).catch(() => ({ data: [] })),
          agentApi.activityStats().catch(() => ({})),
        ]);
        setData(h.data || []);
        setStats(s);
      } catch {}
    };
    load();
    const i = setInterval(load, 30000);
    return () => clearInterval(i);
  }, []);

  // Group into weeks (7-day columns)
  const weeks = useMemo(() => {
    const w: Array<Array<Record<string, unknown>>> = [];
    for (let i = 0; i < data.length; i += 7) {
      w.push(data.slice(i, i + 7));
    }
    return w;
  }, [data]);

  const levels = [
    "bg-muted/30",
    "bg-emerald-500/30",
    "bg-emerald-500/50",
    "bg-emerald-500/70",
    "bg-emerald-500",
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" />
          Activity (90 days)
        </h4>
        <div className="flex gap-3 text-[10px] text-muted-foreground">
          <span>Streak: <span className="text-primary font-mono">{Number(stats.current_streak || 0)}</span></span>
          <span>Total: <span className="text-primary font-mono">{Number(stats.total_tasks || 0)}</span></span>
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto no-scrollbar pb-2">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {week.map((day, di) => {
              const level = Number(day.level || 0);
              const date = String(day.date || "");
              const total = Number(day.total || 0);
              return (
                <motion.div
                  key={di}
                  className={`w-2.5 h-2.5 rounded-sm ${levels[level]} ${day.is_today ? "ring-1 ring-primary ring-offset-1 ring-offset-background" : ""}`}
                  title={`${date}: ${total} tasks`}
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: (wi * 7 + di) * 0.005 }}
                  whileHover={{ scale: 1.3 }}
                />
              );
            })}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-end gap-1 mt-2 text-[9px] text-muted-foreground">
        <span>Less</span>
        {levels.map((l, i) => (
          <div key={i} className={`w-2 h-2 rounded-sm ${l}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

// ============ Cost Panel ============
export function CostPanel() {
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [period, setPeriod] = useState<"today" | "week" | "month" | "all">("month");

  useEffect(() => {
    const load = async () => {
      try {
        const s = await agentApi.costStats(period);
        setStats(s);
      } catch {}
    };
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [period]);

  const totalCost = Number(stats.total_cost_usd || 0);
  const totalCalls = Number(stats.total_calls || 0);
  const tokensIn = Number(stats.total_tokens_in || 0);
  const tokensOut = Number(stats.total_tokens_out || 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <DollarSign className="w-3.5 h-3.5" />
          Cost Tracker
        </h4>
        <div className="flex gap-0.5">
          {(["today", "week", "month", "all"] as const).map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-1.5 py-0.5 text-[9px] rounded font-mono uppercase transition-all ${
                period === p ? "bg-primary/20 text-primary border border-primary/40" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="glass rounded-lg p-2.5">
          <div className="text-[9px] text-muted-foreground uppercase">Total Cost</div>
          <div className="text-lg font-mono font-bold text-emerald-400">
            ${totalCost.toFixed(4)}
          </div>
        </div>
        <div className="glass rounded-lg p-2.5">
          <div className="text-[9px] text-muted-foreground uppercase">API Calls</div>
          <div className="text-lg font-mono font-bold text-cyan-400">
            <AnimatedCounter value={totalCalls} />
          </div>
        </div>
      </div>

      <div className="space-y-1.5 text-[11px]">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Tokens in</span>
          <span className="font-mono">{tokensIn.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Tokens out</span>
          <span className="font-mono">{tokensOut.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Avg / call</span>
          <span className="font-mono">${Number(stats.avg_cost_per_call || 0).toFixed(5)}</span>
        </div>
      </div>

      {/* By model breakdown */}
      {stats.by_model && Object.keys(stats.by_model as Record<string, unknown>).length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/50">
          <div className="text-[9px] text-muted-foreground uppercase mb-1.5">By Model</div>
          <div className="space-y-1">
            {Object.entries(stats.by_model as Record<string, Record<string, number>>).map(([model, m]) => (
              <div key={model} className="flex justify-between text-[10px]">
                <span className="font-mono text-foreground/70">{model}</span>
                <span className="font-mono text-emerald-400">${(m.cost || 0).toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============ Audit Log Panel ============
export function AuditLogPanel() {
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([]);
  const [filterBlocked, setFilterBlocked] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await agentApi.auditRecent({ limit: 30, only_blocked: filterBlocked });
        setEntries(r.entries || []);
      } catch {}
    };
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, [filterBlocked]);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Shield className="w-3.5 h-3.5" />
          Audit Log
        </h4>
        <button
          onClick={() => setFilterBlocked(!filterBlocked)}
          className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase transition-all ${
            filterBlocked ? "bg-red-500/20 text-red-400 border border-red-500/40" : "text-muted-foreground"
          }`}
        >
          {filterBlocked ? "Blocked only" : "All"}
        </button>
      </div>

      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {entries.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">No entries</p>
        ) : (
          entries.map((entry, i) => {
            const action = String(entry.action || "");
            const success = entry.success as boolean;
            const allowed = entry.allowed as boolean;
            const source = String(entry.source || "");
            const time = entry.datetime ? new Date(String(entry.datetime)).toLocaleTimeString(undefined, { hour12: false }) : "";

            return (
              <motion.div
                key={i}
                className="flex items-center gap-2 text-[10px] py-1 px-1.5 rounded hover:bg-accent/20"
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
              >
                <span className="text-zinc-600 font-mono w-12 flex-shrink-0">{time}</span>
                {!allowed ? (
                  <Ban className="w-3 h-3 text-red-500 flex-shrink-0" />
                ) : success ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                ) : (
                  <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                )}
                <span className="font-mono text-primary truncate flex-1">{action}</span>
                <span className="text-muted-foreground font-mono text-[9px] flex-shrink-0">{source}</span>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============ Scheduled Tasks Panel ============
export function ScheduledTasksPanel() {
  const [tasks, setTasks] = useState<Array<Record<string, unknown>>>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({ name: "", request: "", schedule_type: "interval", schedule_expr: "3600" });

  const load = async () => {
    try {
      const r = await agentApi.scheduledList();
      setTasks(r.tasks || []);
    } catch {}
  };

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => {
      await load();
      if (cancelled) return;
    };
    doLoad();
    const i = setInterval(doLoad, 10000);
    return () => { cancelled = true; clearInterval(i); };
  }, []);

  const create = async () => {
    if (!newTask.name || !newTask.request) return;
    try {
      await agentApi.scheduledCreate(newTask);
      setNewTask({ name: "", request: "", schedule_type: "interval", schedule_expr: "3600" });
      setShowCreate(false);
      load();
    } catch {}
  };

  const toggle = async (id: string, enabled: boolean) => {
    await agentApi.scheduledUpdate(id, { enabled: !enabled });
    load();
  };

  const remove = async (id: string) => {
    await agentApi.scheduledDelete(id);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Clock className="w-3.5 h-3.5" />
          Scheduled Tasks
        </h4>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-[10px] px-1.5 py-0.5 rounded bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 transition-all flex items-center gap-1"
        >
          <Plus className="w-2.5 h-2.5" />
          New
        </button>
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mb-3"
          >
            <div className="glass rounded-lg p-3 space-y-2">
              <input
                placeholder="Task name"
                value={newTask.name}
                onChange={e => setNewTask({ ...newTask, name: e.target.value })}
                className="w-full bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50 focus:border-primary/50"
              />
              <textarea
                placeholder="Request in natural language"
                value={newTask.request}
                onChange={e => setNewTask({ ...newTask, request: e.target.value })}
                rows={2}
                className="w-full bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50 focus:border-primary/50 resize-none"
              />
              <div className="flex gap-2">
                <select
                  value={newTask.schedule_type}
                  onChange={e => setNewTask({ ...newTask, schedule_type: e.target.value })}
                  className="bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50"
                >
                  <option value="interval">Interval (s)</option>
                  <option value="cron">Cron</option>
                  <option value="date">One-time</option>
                </select>
                <input
                  placeholder="3600 (seconds) or cron expr"
                  value={newTask.schedule_expr}
                  onChange={e => setNewTask({ ...newTask, schedule_expr: e.target.value })}
                  className="flex-1 bg-background/50 rounded px-2 py-1 text-xs font-mono outline-none border border-border/50 focus:border-primary/50"
                />
              </div>
              <button
                onClick={create}
                className="w-full bg-primary/20 text-primary border border-primary/40 rounded py-1 text-xs hover:bg-primary/30 transition-all"
              >
                Create
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
        {tasks.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">No scheduled tasks</p>
        ) : (
          tasks.map((task, i) => {
            const enabled = task.enabled as boolean;
            return (
              <motion.div
                key={i}
                className="glass rounded-lg p-2 flex items-center gap-2"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <button
                  onClick={() => toggle(String(task.id), enabled)}
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${enabled ? "bg-emerald-500" : "bg-zinc-600"}`}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs truncate">{String(task.name || "")}</div>
                  <div className="text-[9px] text-muted-foreground font-mono truncate">
                    {String(task.schedule_type)}: {String(task.schedule_expr)}
                  </div>
                </div>
                <button
                  onClick={() => remove(String(task.id))}
                  className="text-muted-foreground hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============ Knowledge Base Panel ============
export function KnowledgeBasePanel() {
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<Record<string, unknown>>>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const s = await agentApi.kbStats();
        setStats(s);
      } catch {}
    };
    load();
    const i = setInterval(load, 30000);
    return () => clearInterval(i);
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const r = await agentApi.kbSearch(query, 5);
      setResults((r.results as Array<Record<string, unknown>>) || []);
    } catch {}
    setSearching(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <BookOpen className="w-3.5 h-3.5" />
          Knowledge Base
        </h4>
        <span className="text-[10px] text-muted-foreground font-mono">
          {Number(stats.document_count || 0)} docs · {Number(stats.total_chunks || 0)} chunks
        </span>
      </div>

      <div className="flex gap-1.5 mb-2">
        <input
          placeholder="Semantic search..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && search()}
          className="flex-1 bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50 focus:border-primary/50"
        />
        <button
          onClick={search}
          disabled={searching}
          className="bg-primary/15 text-primary border border-primary/30 rounded px-2 hover:bg-primary/25 transition-all"
        >
          <Search className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
        {results.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-3">
            {query ? "No results" : "Search to find documents"}
          </p>
        ) : (
          results.map((r, i) => (
            <motion.div
              key={i}
              className="glass rounded p-2"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-primary truncate">
                  {String(r.doc_name || "")}
                </span>
                <span className="text-[9px] text-muted-foreground font-mono">
                  {(Number(r.score || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground line-clamp-2">
                {String(r.text || "")}
              </p>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}

// ============ Notifications History Panel ============
export function NotificationsPanel() {
  const [notifications, setNotifications] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await agentApi.notifications(20);
        setNotifications(r.notifications || []);
      } catch {}
    };
    load();
    const i = setInterval(load, 10000);
    return () => clearInterval(i);
  }, []);

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
        <Bell className="w-3.5 h-3.5" />
        Notifications
      </h4>
      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
        {notifications.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">No notifications yet</p>
        ) : (
          notifications.map((n, i) => {
            const time = n.datetime ? new Date(String(n.datetime)).toLocaleTimeString(undefined, { hour12: false }) : "";
            const msg = String((n.params as Record<string, unknown>)?.text || (n.params as Record<string, unknown>)?.message || "Notification");
            return (
              <motion.div
                key={i}
                className="glass rounded p-2 flex items-start gap-2"
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
              >
                <Bell className="w-2.5 h-2.5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] truncate">{msg}</p>
                  <span className="text-[9px] text-muted-foreground font-mono">{time}</span>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
