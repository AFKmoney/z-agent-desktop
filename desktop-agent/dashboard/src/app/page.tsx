"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Activity, Send, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, CheckCircle2, XCircle,
  Camera, FileText, Mail, Calendar, Globe, Monitor, MonitorSmartphone,
  Lightbulb, Eye, Languages, Sparkles, Search, Code, Network,
  Mic, Plug, Radio, MessageSquare, Command, Volume2, Settings,
} from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi, type TaskRecord } from "@/lib/agent-api";
import { t, detectBrowserLang, setStoredLang, stateLabel, type Lang } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  AnimatedCounter, StateOrb, GlassCard, StatPill, ModuleTile,
  ThinkingStream, TaskCard, CommandPalette, ParticleBackground, VoiceWaveform,
} from "@/components/agent";
import {
  ActivityHeatmap, CostPanel, AuditLogPanel, ScheduledTasksPanel,
  KnowledgeBasePanel, NotificationsPanel,
} from "@/components/agent/panels";
import {
  LLMProviderSwitcher, SmartSuggestionsPanel, PromptTemplatesPanel, BackupPanel,
} from "@/components/agent/power-panels";
import { SettingsModal } from "@/components/agent/settings-modal";

const MODULES_LIST = ["screen", "files", "email", "calendar", "browser", "system", "windows", "code", "web", "voice", "plugin", "mcp", "vision", "slack"];

const CAPABILITIES = [
  { icon: Sparkles, label_en: "ReAct loop", label_fr: "Boucle ReAct", color: "#10B981" },
  { icon: Code, label_en: "Code interpreter", label_fr: "Interpréteur code", color: "#06B6D4" },
  { icon: Search, label_en: "Web search", label_fr: "Recherche web", color: "#06B6D4" },
  { icon: Network, label_en: "Multi-agent", label_fr: "Multi-agent", color: "#EC4899" },
  { icon: Brain, label_en: "Skill library", label_fr: "Bibliothèque skills", color: "#10B981" },
  { icon: Zap, label_en: "GLM tool calling", label_fr: "GLM tool calling", color: "#F59E0B" },
  { icon: Mic, label_en: "Voice control", label_fr: "Contrôle vocal", color: "#F59E0B" },
  { icon: MessageSquare, label_en: "Long context", label_fr: "Contexte long", color: "#8B5CF6" },
  { icon: Plug, label_en: "Plugin marketplace", label_fr: "Marché plugins", color: "#8B5CF6" },
  { icon: Network, label_en: "MCP protocol", label_fr: "Protocole MCP", color: "#EC4899" },
  { icon: Radio, label_en: "Vision streaming", label_fr: "Vision streaming", color: "#10B981" },
  { icon: Cpu, label_en: "100% Windows", label_fr: "100% Windows", color: "#3B82F6" },
];

const QUICK_ACTIONS = [
  { icon: FileText, label_en: "Sort Downloads", label_fr: "Trier Téléch.", prompt_en: "Organize my Downloads folder by file type", prompt_fr: "Organise mon dossier Téléchargements par type de fichier", color: "#10B981" },
  { icon: Mail, label_en: "Read emails", label_fr: "Lire emails", prompt_en: "Read my 5 latest unread emails and summarize them", prompt_fr: "Lis mes 5 derniers emails non lus et fais-moi un résumé", color: "#F59E0B" },
  { icon: Calendar, label_en: "Events", label_fr: "Événements", prompt_en: "List my 10 upcoming calendar events", prompt_fr: "Liste mes 10 prochains événements de calendrier", color: "#8B5CF6" },
  { icon: Monitor, label_en: "Describe screen", label_fr: "Décrire écran", prompt_en: "Describe what's currently on my screen", prompt_fr: "Décris ce qu'il y a actuellement sur mon écran", color: "#06B6D4" },
  { icon: Cpu, label_en: "System info", label_fr: "Infos système", prompt_en: "Give me system info (CPU, RAM, disk)", prompt_fr: "Donne-moi les informations système (CPU, RAM, disque)", color: "#EC4899" },
  { icon: Camera, label_en: "Screenshot", label_fr: "Capture", prompt_en: "Take a screenshot and analyze it", prompt_fr: "Prends une capture d'écran et analyse-la", color: "#10B981" },
];

export default function Dashboard() {
  const [lang, setLang] = useState<Lang>("en");
  useEffect(() => setLang(detectBrowserLang()), []);

  const { status, logs, progress, connected, refresh } = useAgent();
  const { toast } = useToast();
  const [taskInput, setTaskInput] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [screenshots, setScreenshots] = useState<Array<{ name: string; size: number; modified: number }>>([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeView, setActiveView] = useState<"stream" | "tasks" | "logs" | "screens">("stream");
  const [liveTrace, setLiveTrace] = useState<Array<Record<string, unknown>>>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const tr = useCallback((key: string, vars?: Record<string, string | number>) => t(key, lang, vars), [lang]);

  // Cmd+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Load data
  const loadData = useCallback(async () => {
    try {
      const [tasksRes, shotsRes] = await Promise.all([
        agentApi.recentTasks(20).catch(() => ({ tasks: [] as TaskRecord[] })),
        agentApi.screenshots(8).catch(() => ({ screenshots: [] })),
      ]);
      setTasks(tasksRes.tasks || []);
      setScreenshots(shotsRes.screenshots || []);
    } catch {}
  }, []);

  useEffect(() => {
    loadData();
    const i = setInterval(loadData, 5000);
    return () => clearInterval(i);
  }, [loadData, progress]);

  // Update live trace from progress events
  useEffect(() => {
    if (progress.length === 0) return;
    const lastEvent = progress[progress.length - 1];
    if (lastEvent.event === "react_thought" || lastEvent.event === "react_step") {
      setLiveTrace(prev => {
        const newEntry: Record<string, unknown> = {
          turn: (lastEvent as Record<string, unknown>).turn,
          thought: (lastEvent as Record<string, unknown>).thought,
          action: (lastEvent as Record<string, unknown>).action,
          observation: (lastEvent as Record<string, unknown>).observation,
          success: (lastEvent as Record<string, unknown>).success,
        };
        return [...prev.slice(-30), newEntry];
      });
    }
    if (lastEvent.event === "task_end" || lastEvent.event === "task_start") {
      setTimeout(() => { setLiveTrace([]); refresh(); loadData(); }, 500);
    }
  }, [progress, refresh, loadData]);

  useEffect(() => {
    if (activeView === "logs" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, activeView]);

  const submitTask = async (text?: string) => {
    const request = (text || taskInput).trim();
    if (!request) return;
    setSubmitting(true);
    try {
      await agentApi.submitTask(request, "dashboard");
      setTaskInput("");
      setLiveTrace([]);
      setActiveView("stream");
      toast({ title: lang === "fr" ? "Tâche envoyée" : "Task sent" });
      setTimeout(loadData, 500);
    } catch (e) {
      toast({ title: tr("toast.error"), description: e instanceof Error ? e.message : "", variant: "destructive" });
    } finally { setSubmitting(false); }
  };

  const sendCommand = async (cmd: "pause" | "resume" | "stop" | "start") => {
    try {
      await agentApi.command(cmd);
      setTimeout(refresh, 200);
    } catch {}
  };

  const state = status?.state ?? "stopped";
  const currentTask = status?.current_task;
  const memory = status?.memory;
  const isLive = state === "planning" || state === "executing";

  return (
    <div className="min-h-screen bg-background relative">
      <ParticleBackground />

      {/* Header */}
      <header className="sticky top-0 z-40 glass-strong border-b border-border/50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <motion.div
              className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/30 to-accent/30 border border-primary/40 flex items-center justify-center"
              animate={{ boxShadow: ["0 0 20px oklch(0.78 0.18 165 / 0.3)", "0 0 30px oklch(0.78 0.18 165 / 0.5)", "0 0 20px oklch(0.78 0.18 165 / 0.3)"] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Bot className="w-5 h-5 text-primary" />
            </motion.div>
            <div>
              <h1 className="text-base font-bold tracking-tight leading-none">
                Z.AGENT
                <span className="ml-2 text-[10px] font-mono text-muted-foreground">v3.0</span>
              </h1>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {connected ? "● connected" : "○ offline"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" variant="ghost" onClick={() => setPaletteOpen(true)} className="gap-2 text-xs">
              <Command className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{lang === "fr" ? "Commande" : "Command"}</span>
              <kbd className="text-[9px] font-mono bg-muted/60 px-1 py-0.5 rounded">⌘K</kbd>
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSettingsOpen(true)} className="gap-1.5 text-xs px-2" title={lang === "fr" ? "Paramètres" : "Settings"}>
              <Settings className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{lang === "fr" ? "Paramètres" : "Settings"}</span>
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setLang(lang === "fr" ? "en" : "fr")} className="gap-1.5 font-mono text-xs px-2">
              <Languages className="w-3.5 h-3.5" />
              {lang.toUpperCase()}
            </Button>
            <div className="flex gap-0.5 border-l border-border pl-2 ml-1">
              <Button size="sm" variant="ghost" onClick={() => sendCommand("pause")} disabled={!isLive && state !== "idle"} className="h-8 w-8 p-0">
                <Pause className="w-3.5 h-3.5" />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => sendCommand("resume")} disabled={state !== "paused"} className="h-8 w-8 p-0">
                <Play className="w-3.5 h-3.5" />
              </Button>
              <Button size="sm" variant="ghost" onClick={refresh} className="h-8 w-8 p-0">
                <RefreshCw className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* Hero strip — State orb + stats */}
        <motion.div
          className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-6"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <GlassCard className="lg:col-span-3 p-6 flex flex-col items-center justify-center" glow={isLive}>
            <StateOrb state={state} lang={lang} />
          </GlassCard>

          <div className="lg:col-span-9 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <StatPill icon={Activity} label={tr("label.state")} value={stateLabel(state, lang)} color="#10B981" />
            <StatPill icon={Clock} label={tr("label.queue")} value={status?.queue_size ?? 0} color="#06B6D4" />
            <StatPill icon={Brain} label={tr("dash.facts")} value={memory?.facts_count ?? 0} color="#8B5CF6" />
            <StatPill icon={Zap} label={tr("dash.tasks")} value={memory?.tasks_count ?? 0} color="#F59E0B" />
            <StatPill icon={Cpu} label={tr("label.uptime")} value={`${Math.floor((status?.uptime_s ?? 0) / 60)}m`} color="#EC4899" />
          </div>
        </motion.div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left sidebar — Modules + Capabilities */}
          <div className="lg:col-span-3 space-y-4">
            <GlassCard className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5" />
                {lang === "fr" ? "Modules" : "Modules"}
              </h3>
              <div className="grid grid-cols-3 gap-2">
                {MODULES_LIST.map((m, i) => (
                  <motion.div
                    key={m}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <ModuleTile name={m} />
                  </motion.div>
                ))}
              </div>
            </GlassCard>

            <GlassCard className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5" />
                {lang === "fr" ? "Capacités" : "Capabilities"}
              </h3>
              <div className="space-y-2">
                {CAPABILITIES.map((cap, i) => {
                  const Icon = cap.icon;
                  return (
                    <motion.div
                      key={i}
                      className="flex items-center gap-2.5 text-xs group"
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.4 + i * 0.03 }}
                    >
                      <div
                        className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110"
                        style={{ background: `${cap.color}15`, border: `1px solid ${cap.color}30` }}
                      >
                        <Icon className="w-3 h-3" style={{ color: cap.color }} />
                      </div>
                      <span className="text-foreground/80">
                        {lang === "fr" ? cap.label_fr : cap.label_en}
                      </span>
                      <Circle className="w-1 h-1 fill-emerald-500 text-emerald-500 ml-auto flex-shrink-0" />
                    </motion.div>
                  );
                })}
              </div>
            </GlassCard>
          </div>

          {/* Center — main interaction */}
          <div className="lg:col-span-6 space-y-4">
            {/* Task input */}
            <GlassCard className="p-4" glow={isLive}>
              <div className="flex items-center gap-2 mb-3">
                <Send className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold">{tr("dash.submit_task")}</h3>
                {isLive && (
                  <motion.span
                    className="ml-auto text-[10px] font-mono uppercase text-primary flex items-center gap-1"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <VoiceWaveform active={isLive} />
                    {lang === "fr" ? "agent actif" : "agent busy"}
                  </motion.span>
                )}
              </div>
              <Textarea
                placeholder={tr("dash.task_placeholder")}
                value={taskInput}
                onChange={e => setTaskInput(e.target.value)}
                rows={2}
                className="resize-none bg-background/50 border-border/50 focus:border-primary/50"
                onKeyDown={e => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitTask();
                }}
              />
              <SmartSuggestionsPanel
                currentRequest={taskInput}
                onPick={(s) => setTaskInput(s)}
              />
              <div className="flex flex-wrap gap-1.5 mt-3">
                {QUICK_ACTIONS.map(qa => {
                  const Icon = qa.icon;
                  return (
                    <button
                      key={qa.label_en}
                      onClick={() => setTaskInput(lang === "fr" ? qa.prompt_fr : qa.prompt_en)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border border-border/50 bg-card/30 hover:bg-accent/30 transition-all hover:scale-105"
                      style={{ borderColor: `${qa.color}30` }}
                    >
                      <Icon className="w-3 h-3" style={{ color: qa.color }} />
                      {lang === "fr" ? qa.label_fr : qa.label_en}
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-between items-center mt-3">
                <span className="text-[10px] text-muted-foreground font-mono">⌘+Enter · ⌘K</span>
                <Button
                  size="sm"
                  onClick={() => submitTask()}
                  disabled={!taskInput.trim() || submitting}
                  className="gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? (lang === "fr" ? "Envoi..." : "Sending...") : tr("dash.send")}
                </Button>
              </div>
            </GlassCard>

            {/* Current task banner */}
            {currentTask && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                <GlassCard className="p-4 border-primary/30" glow>
                  <div className="flex items-center gap-2 mb-2">
                    <motion.div
                      className="w-2 h-2 rounded-full bg-primary"
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />
                    <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                      {tr("dash.current_task")}
                    </span>
                  </div>
                  <p className="text-sm">{currentTask.request}</p>
                </GlassCard>
              </motion.div>
            )}

            {/* View tabs */}
            <div className="flex gap-1 border-b border-border/50">
              {[
                { id: "stream", label: lang === "fr" ? "Raisonnement" : "Thinking", icon: Brain, count: liveTrace.length },
                { id: "tasks", label: tr("dash.tasks"), icon: FileText, count: tasks.length },
                { id: "logs", label: tr("dash.logs"), icon: Terminal, count: logs.length },
                { id: "screens", label: tr("dash.screenshots"), icon: ImageIcon, count: screenshots.length },
              ].map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveView(tab.id as typeof activeView)}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-all relative",
                      activeView === tab.id
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {tab.label}
                    {tab.count > 0 && (
                      <span className="text-[9px] font-mono bg-muted/60 px-1.5 py-0.5 rounded">
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* View content */}
            <div className="min-h-[400px]">
              <AnimatePresence mode="wait">
                {activeView === "stream" && (
                  <motion.div key="stream" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <GlassCard className="p-4">
                      <ThinkingStream traces={liveTrace} live={isLive} />
                    </GlassCard>
                  </motion.div>
                )}

                {activeView === "tasks" && (
                  <motion.div key="tasks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2">
                    {tasks.length === 0 ? (
                      <GlassCard className="p-8 text-center text-sm text-muted-foreground">
                        <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                        {tr("dash.no_tasks")}
                      </GlassCard>
                    ) : (
                      tasks.map((task, i) => <TaskCard key={task.task_id || i} task={task as Record<string, unknown>} lang={lang} />)
                    )}
                  </motion.div>
                )}

                {activeView === "logs" && (
                  <motion.div key="logs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <GlassCard className="p-3 font-mono text-xs max-h-[500px] overflow-y-auto">
                      {logs.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                          <Terminal className="w-10 h-10 mx-auto mb-3 opacity-30" />
                          {tr("dash.no_logs")}
                        </div>
                      ) : (
                        logs.map((log, i) => {
                          const colors: Record<string, string> = {
                            INFO: "text-emerald-400", WARNING: "text-amber-400",
                            ERROR: "text-red-400", DEBUG: "text-zinc-500",
                          };
                          const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString(undefined, { hour12: false }) : "";
                          return (
                            <div key={i} className="flex gap-2 leading-relaxed hover:bg-accent/20 -mx-1 px-1 rounded">
                              <span className="text-zinc-600 flex-shrink-0">{time}</span>
                              <span className={cn("flex-shrink-0 w-12", colors[log.level] || "text-zinc-400")}>{log.level}</span>
                              <span className="text-zinc-500 flex-shrink-0 w-16 truncate">{log.logger}</span>
                              <span className="text-foreground/90 break-all">{log.message}</span>
                            </div>
                          );
                        })
                      )}
                      <div ref={logsEndRef} />
                    </GlassCard>
                  </motion.div>
                )}

                {activeView === "screens" && (
                  <motion.div key="screens" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <GlassCard className="p-4">
                      {screenshots.length === 0 ? (
                        <div className="p-8 text-center text-sm text-muted-foreground">
                          <ImageIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
                          {tr("dash.no_screenshots")}
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          {screenshots.map(shot => <ScreenshotTile key={shot.name} shot={shot} />)}
                        </div>
                      )}
                    </GlassCard>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Right — Memory + tip */}
          <div className="lg:col-span-3 space-y-4">
            <GlassCard className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Brain className="w-3.5 h-3.5" />
                {tr("dash.memory")}
              </h3>
              <div className="space-y-3">
                <MemoryBar label={tr("dash.facts")} value={memory?.facts_count ?? 0} max={100} color="#8B5CF6" />
                <MemoryBar label={tr("dash.preferences")} value={memory?.preferences_count ?? 0} max={20} color="#06B6D4" />
                <MemoryBar label={tr("dash.shortcuts")} value={memory?.shortcuts_count ?? 0} max={50} color="#F59E0B" />
              </div>
              <div className="mt-4 pt-3 border-t border-border/50">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                  {tr("dash.recent_tasks")}
                </p>
                <div className="space-y-1">
                  {memory?.recent_tasks?.slice(0, 5).map((task, i) => {
                    const t = task as Record<string, unknown>;
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        {t.success ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                        )}
                        <span className="truncate text-muted-foreground">
                          {String(t.request || "").slice(0, 35)}
                        </span>
                      </div>
                    );
                  }) ?? (
                    <p className="text-xs text-muted-foreground">{tr("misc.no_recent_tasks")}</p>
                  )}
                </div>
              </div>
            </GlassCard>

            <GlassCard className="p-4 bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
              <div className="flex items-start gap-3">
                <Lightbulb className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold mb-1">{tr("misc.tip_title")}</p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {tr("misc.tip_body")}
                  </p>
                </div>
              </div>
            </GlassCard>

            <GlassCard className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Eye className="w-3.5 h-3.5" />
                {tr("dash.vlm_perception")}
              </h3>
              <p className="text-[11px] text-muted-foreground mb-3">
                {tr("dash.vlm_description")}
              </p>
              <Button size="sm" variant="outline" className="w-full gap-2" onClick={() => {
                agentApi.captureScreenshot().then(() => setTimeout(loadData, 500)).catch(() => {});
              }}>
                <Camera className="w-3.5 h-3.5" />
                {tr("dash.analyze_screen")}
              </Button>
            </GlassCard>
          </div>
        </div>

        {/* Insights row — full-width analytics panels */}
        <motion.div
          className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <GlassCard className="p-4 lg:col-span-2">
            <ActivityHeatmap />
          </GlassCard>

          <GlassCard className="p-4">
            <CostPanel />
          </GlassCard>

          <GlassCard className="p-4">
            <AuditLogPanel />
          </GlassCard>

          <GlassCard className="p-4">
            <ScheduledTasksPanel />
          </GlassCard>

          <GlassCard className="p-4">
            <KnowledgeBasePanel />
          </GlassCard>

          <GlassCard className="p-4">
            <NotificationsPanel />
          </GlassCard>

          <GlassCard className="p-4">
            <LLMProviderSwitcher />
          </GlassCard>

          <GlassCard className="p-4">
            <PromptTemplatesPanel onUse={(tpl) => setTaskInput(tpl)} />
          </GlassCard>

          <GlassCard className="p-4">
            <BackupPanel />
          </GlassCard>
        </motion.div>
      </main>

      <footer className="border-t border-border/50 mt-12 py-4">
        <div className="container mx-auto px-4 flex justify-between items-center text-[10px] text-muted-foreground font-mono">
          <span>Z.AGENT v4.0 · {lang === "fr" ? "propulsé par z.ai GLM" : "powered by z.ai GLM"}</span>
          <span className="flex items-center gap-1.5">
            <span className={cn("w-1.5 h-1.5 rounded-full", connected ? "bg-emerald-500" : "bg-red-500")} />
            {state}
          </span>
        </div>
      </footer>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onSubmit={submitTask} />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} lang={lang} />
    </div>
  );
}

// === Sub-components ===

function MemoryBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 bg-muted/40 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 10px ${color}80` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

function ScreenshotTile({ shot }: { shot: { name: string; size: number; modified: number } }) {
  const [errored, setErrored] = useState(false);
  const src = useMemo(() => {
    try { return agentApi.screenshotUrl(shot.name); } catch { return null; }
  }, [shot.name]);
  const time = new Date(shot.modified * 1000).toLocaleTimeString(undefined, { hour: 2, minute: 2, second: 2 });

  return (
    <motion.div
      className="relative group rounded-lg overflow-hidden border border-border/50 bg-card/50"
      whileHover={{ scale: 1.03 }}
      transition={{ type: "spring", damping: 20 }}
    >
      {src && !errored ? (
        <img src={src} alt={shot.name} className="w-full aspect-video object-cover" loading="lazy" onError={() => setErrored(true)} />
      ) : (
        <div className="w-full aspect-video flex items-center justify-center bg-muted/30">
          <ImageIcon className="w-6 h-6 text-muted-foreground/50" />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
        <div>
          <p className="text-[9px] font-mono text-white/90 truncate">{shot.name}</p>
          <p className="text-[9px] text-white/60">{time}</p>
        </div>
      </div>
    </motion.div>
  );
}
